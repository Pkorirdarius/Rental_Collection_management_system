import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.audit import audit
from apps.core.models import AuditLog
from apps.ledger.models import LedgerEntry

ZERO = Decimal("0.00")
DEPOSIT_TYPES = {LedgerEntry.Type.DEPOSIT, LedgerEntry.Type.DEPOSIT_REFUND}
RENT_TYPES = {
    LedgerEntry.Type.RENT_CHARGE,
    LedgerEntry.Type.LATE_FEE,
    LedgerEntry.Type.PAYMENT,
    LedgerEntry.Type.ADJUSTMENT,
    LedgerEntry.Type.WAIVER,
    LedgerEntry.Type.REVERSAL,
}
CHARGE_TYPES = {LedgerEntry.Type.RENT_CHARGE, LedgerEntry.Type.LATE_FEE}


def month_bounds(day: date) -> tuple[date, date]:
    start = day.replace(day=1)
    last = calendar.monthrange(start.year, start.month)[1]
    return start, start.replace(day=last)


def add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def rent_entries(lease):
    return LedgerEntry.objects.filter(lease=lease, entry_type__in=RENT_TYPES)


def lease_balance(lease) -> Decimal:
    total = rent_entries(lease).aggregate(total=Sum("amount"))["total"]
    return (total or ZERO).quantize(Decimal("0.01"))


def lease_status(lease, day: date | None = None) -> str:
    day = day or timezone.localdate()
    if lease.status not in {"ACTIVE", "ENDED"}:
        return "INACTIVE"
    if lease_balance(lease) <= ZERO:
        return "PAID"
    if day < lease.start_date:
        return "PARTIAL"
    charges = outstanding_charges(lease, day)
    if not charges:
        return "PAID"
    oldest_due = min(charge["due_date"] for charge in charges)
    grace_end = oldest_due + timedelta(days=lease.grace_period_days)
    return "OVERDUE" if day > grace_end else "PARTIAL"


def days_overdue(lease, day: date | None = None) -> int:
    day = day or timezone.localdate()
    if lease_balance(lease) <= ZERO:
        return 0
    charges = outstanding_charges(lease, day)
    if not charges:
        return 0
    oldest_due = min(charge["due_date"] for charge in charges)
    grace_end = oldest_due + timedelta(days=lease.grace_period_days)
    return max(0, (day - grace_end).days)


def post_entry(
    *,
    lease,
    entry_type,
    amount,
    effective_date=None,
    description="",
    source=LedgerEntry.Source.MANUAL,
    payment=None,
    period_start=None,
    period_end=None,
    reversal_of=None,
    idempotency_key=None,
    metadata=None,
    created_by=None,
):
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount == ZERO:
        raise ValueError("Ledger amount cannot be zero")
    effective_date = effective_date or timezone.localdate()
    if idempotency_key:
        existing = LedgerEntry.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing, False
    try:
        with transaction.atomic():
            entry = LedgerEntry.objects.create(
                organization=lease.organization,
                lease=lease,
                tenant=lease.tenant,
                unit=lease.unit,
                entry_type=entry_type,
                amount=amount,
                effective_date=effective_date,
                period_start=period_start,
                period_end=period_end,
                description=description[:255],
                source=source,
                payment=payment,
                reversal_of=reversal_of,
                idempotency_key=idempotency_key,
                metadata=metadata or {},
                created_by=created_by,
            )
    except IntegrityError:
        existing = LedgerEntry.objects.get(idempotency_key=idempotency_key)
        return existing, False
    audit(
        AuditLog.Action.LEDGER_POSTED,
        obj=entry,
        organization=entry.organization,
        changes={"entry_type": entry_type, "amount": str(amount)},
    )
    return entry, True


def post_rent_charge(lease, *, period_start, period_end, amount, due_date=None, created_by=None):
    key = f"rent:{lease.id}:{period_start:%Y-%m}"
    return post_entry(
        lease=lease,
        entry_type=LedgerEntry.Type.RENT_CHARGE,
        amount=Decimal(str(amount)),
        effective_date=period_start,
        period_start=period_start,
        period_end=period_end,
        description=f"Rent {period_start:%B %Y}",
        source=LedgerEntry.Source.SYSTEM,
        idempotency_key=key,
        metadata={"due_date": (due_date or lease.due_date_for(period_start)).isoformat()},
        created_by=created_by,
    )


def post_payment(
    lease,
    *,
    amount,
    payment=None,
    effective_date=None,
    source=LedgerEntry.Source.CASH,
    description="",
    created_by=None,
    idempotency_key=None,
):
    return post_entry(
        lease=lease,
        entry_type=LedgerEntry.Type.PAYMENT,
        amount=-abs(Decimal(str(amount))),
        effective_date=effective_date or timezone.localdate(),
        description=description or "Rent payment",
        source=source,
        payment=payment,
        created_by=created_by,
        idempotency_key=idempotency_key or (f"payment:{payment.id}" if payment else None),
    )


def post_reversal(entry, *, reason="", created_by=None):
    key = f"reversal:{entry.id}"
    return post_entry(
        lease=entry.lease,
        entry_type=LedgerEntry.Type.REVERSAL,
        amount=-entry.amount,
        effective_date=timezone.localdate(),
        description=f"Reversal of {entry.entry_type}: {reason}"[:255],
        source=LedgerEntry.Source.MANUAL,
        reversal_of=entry,
        idempotency_key=key,
        metadata={"reason": reason},
        created_by=created_by,
    )


def prorated_rent(lease, period_start, period_end) -> Decimal:
    if not lease.proration_enabled:
        return lease.rent_amount
    days_in_month = (period_end - period_start).days + 1
    active_start = max(period_start, lease.start_date)
    active_end = min(period_end, lease.end_date or period_end)
    if active_end < active_start:
        return ZERO
    active_days = (active_end - active_start).days + 1
    if active_days >= days_in_month:
        return lease.rent_amount
    return (lease.rent_amount * Decimal(active_days) / Decimal(days_in_month)).quantize(
        Decimal("0.01")
    )


def generate_rent_charges(year: int, month: int, organization=None) -> dict:
    from apps.leases.models import Lease

    period_start = date(year, month, 1)
    period_end = date(year, month, calendar.monthrange(year, month)[1])
    from django.db.models import Q

    leases = Lease.objects.filter(
        status__in=[Lease.Status.ACTIVE, Lease.Status.ENDED],
        start_date__lte=period_end,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=period_start)
    ).select_related("tenant", "unit", "organization")
    if organization:
        leases = leases.filter(organization=organization)

    created = 0
    skipped = 0
    for lease in leases:
        amount = prorated_rent(lease, period_start, period_end)
        if amount <= ZERO:
            skipped += 1
            continue
        _, was_created = post_rent_charge(
            lease,
            period_start=period_start,
            period_end=period_end,
            amount=amount,
            due_date=lease.due_date_for(period_start),
        )
        created += int(was_created)
        skipped += int(not was_created)
    return {"created": created, "skipped": skipped, "period": f"{year:04d}-{month:02d}"}


def apply_late_fees(organization=None, today: date | None = None) -> dict:
    from apps.leases.models import Lease

    today = today or timezone.localdate()
    period_start, period_end = month_bounds(today)
    leases = Lease.objects.filter(
        status=Lease.Status.ACTIVE, late_fee_type__in=["FLAT", "PERCENT"]
    ).select_related("tenant", "unit", "organization")
    if organization:
        leases = leases.filter(organization=organization)

    applied = 0
    for lease in leases:
        if lease_balance(lease) <= ZERO:
            continue
        due = lease.due_date_for(period_start)
        threshold = due + timedelta(days=lease.grace_period_days if lease.late_fee_applies_after_grace else 0)
        if today <= threshold:
            continue
        if not LedgerEntry.objects.filter(
            lease=lease,
            entry_type=LedgerEntry.Type.RENT_CHARGE,
            period_start=period_start,
        ).exists():
            continue
        if lease.late_fee_type == Lease.LateFeeType.FLAT:
            fee = lease.late_fee_value
        else:
            fee = (lease.rent_amount * lease.late_fee_value / Decimal("100")).quantize(
                Decimal("0.01")
            )
        if fee <= ZERO:
            continue
        _, was_created = post_entry(
            lease=lease,
            entry_type=LedgerEntry.Type.LATE_FEE,
            amount=fee,
            effective_date=today,
            description=f"Late fee {period_start:%B %Y}",
            source=LedgerEntry.Source.SYSTEM,
            idempotency_key=f"latefee:{lease.id}:{period_start:%Y-%m}",
            metadata={"due_date": due.isoformat()},
        )
        applied += int(was_created)
    return {"applied": applied, "date": today.isoformat()}


def outstanding_charges(lease, day: date | None = None) -> list[dict]:
    """FIFO-allocate credits to charges and return the still-outstanding charges."""
    day = day or timezone.localdate()
    entries = rent_entries(lease).order_by("effective_date", "created_at")
    charges: list[dict] = []
    for entry in entries:
        amount = Decimal(entry.amount)
        if amount > ZERO:
            due = entry.metadata.get("due_date") if entry.metadata else None
            charges.append(
                {
                    "entry_id": str(entry.id),
                    "type": entry.entry_type,
                    "date": entry.effective_date,
                    "due_date": date.fromisoformat(due) if due else entry.effective_date,
                    "amount": amount,
                    "remaining": amount,
                }
            )
        elif amount < ZERO:
            credit = -amount
            for charge in charges:
                if credit <= ZERO:
                    break
                if charge["remaining"] <= ZERO:
                    continue
                applied = min(credit, charge["remaining"])
                charge["remaining"] -= applied
                credit -= applied
    result = []
    for charge in charges:
        if charge["remaining"] <= ZERO:
            continue
        overdue_days = max(0, (day - charge["due_date"]).days)
        result.append(
            {
                **charge,
                "remaining": charge["remaining"].quantize(Decimal("0.01")),
                "days_overdue": overdue_days,
                "bucket": ageing_bucket(overdue_days),
            }
        )
    return result


def ageing_bucket(days: int) -> str:
    if days <= 0:
        return "current"
    if days <= 7:
        return "1-7"
    if days <= 30:
        return "8-30"
    return "31+"


def lease_ageing(lease, day: date | None = None) -> dict:
    charges = outstanding_charges(lease, day)
    buckets = defaultdict(lambda: ZERO)
    for charge in charges:
        buckets[charge["bucket"]] += charge["remaining"]
    total = sum((c["remaining"] for c in charges), ZERO)
    return {
        "lease_id": str(lease.id),
        "tenant": lease.tenant.full_name,
        "property": lease.unit.property.name,
        "unit": lease.unit.code,
        "total": total.quantize(Decimal("0.01")),
        "buckets": {k: v.quantize(Decimal("0.01")) for k, v in buckets.items()},
        "days_overdue": days_overdue(lease, day),
        "status": lease_status(lease, day),
        "charges": charges,
    }


def lease_statement(lease) -> dict:
    entries = LedgerEntry.objects.filter(lease=lease).order_by("effective_date", "created_at")
    running = ZERO
    rows = []
    for entry in entries:
        if entry.entry_type not in DEPOSIT_TYPES:
            running += entry.amount
        rows.append(
            {
                "id": str(entry.id),
                "date": entry.effective_date,
                "type": entry.entry_type,
                "description": entry.description,
                "debit": str(entry.amount) if entry.amount > ZERO else "0.00",
                "credit": str(-entry.amount) if entry.amount < ZERO else "0.00",
                "balance": str(running.quantize(Decimal("0.01"))),
                "reference": entry.payment.reference if entry.payment_id else "",
            }
        )
    return {
        "lease_id": str(lease.id),
        "tenant": lease.tenant.full_name,
        "unit": lease.unit.code,
        "property": lease.unit.property.name,
        "balance": str(lease_balance(lease)),
        "status": lease_status(lease),
        "days_overdue": days_overdue(lease),
        "entries": rows,
    }


def tenant_statement(tenant) -> dict:
    leases = tenant.leases.select_related("unit__property").order_by("-start_date")
    return {
        "tenant_id": str(tenant.id),
        "tenant": tenant.full_name,
        "phone": tenant.phone,
        "leases": [lease_statement(lease) for lease in leases],
        "total_balance": str(
            sum((lease_balance(lease) for lease in leases), ZERO).quantize(Decimal("0.01"))
        ),
    }
