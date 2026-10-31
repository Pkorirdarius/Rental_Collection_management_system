from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.ledger.models import LedgerEntry
from apps.ledger.services import (
    ageing_bucket,
    days_overdue,
    lease_ageing,
    lease_balance,
    lease_status,
    month_bounds,
)
from apps.notifications.models import PromiseToPay
from apps.payments.models import Payment

ZERO = Decimal("0.00")
BUCKETS = ["current", "1-7", "8-30", "31+"]


def _month_start(value=None) -> date:
    value = value or timezone.localdate()
    if isinstance(value, str):
        value = date.fromisoformat(value[:7] + "-01")
    return value.replace(day=1)


def dashboard_summary(organization, month=None, property_id=None) -> dict:
    month_start = _month_start(month)
    _, month_end = month_bounds(month_start)
    ledger = LedgerEntry.objects.filter(organization=organization)
    if property_id:
        ledger = ledger.filter(unit__property_id=property_id)

    expected = (
        ledger.filter(
            entry_type=LedgerEntry.Type.RENT_CHARGE, period_start=month_start
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    late_fees = (
        ledger.filter(
            entry_type=LedgerEntry.Type.LATE_FEE,
            effective_date__gte=month_start,
            effective_date__lte=month_end,
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    payments = (
        ledger.filter(
            entry_type=LedgerEntry.Type.PAYMENT,
            effective_date__gte=month_start,
            effective_date__lte=month_end,
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    collected = -payments

    from apps.leases.models import Lease
    from apps.properties.models import Unit

    leases = Lease.objects.filter(organization=organization, status=Lease.Status.ACTIVE)
    units = Unit.objects.filter(organization=organization, deleted_at__isnull=True)
    if property_id:
        leases = leases.filter(unit__property_id=property_id)
        units = units.filter(property_id=property_id)
    leases = leases.select_related("tenant", "unit", "unit__property")

    arrears = ZERO
    status_counts = {"PAID": 0, "PARTIAL": 0, "OVERDUE": 0}
    for lease in leases:
        balance = lease_balance(lease)
        if balance > ZERO:
            arrears += balance
        status = lease_status(lease)
        if status in status_counts:
            status_counts[status] += 1

    total_units = units.count()
    occupied = units.filter(status=Unit.Status.OCCUPIED).count()
    expected_total = expected + late_fees
    rate = float((collected / expected_total) * 100) if expected_total > 0 else 0.0

    unmatched = Payment.objects.filter(
        organization=organization, status=Payment.Status.UNMATCHED
    ).count()
    promises = PromiseToPay.objects.filter(
        organization=organization, status=PromiseToPay.Status.OPEN
    ).count()

    return {
        "month": f"{month_start:%Y-%m}",
        "expected": str(expected_total.quantize(Decimal("0.01"))),
        "rent_expected": str(expected.quantize(Decimal("0.01"))),
        "late_fees": str(late_fees.quantize(Decimal("0.01"))),
        "collected": str(collected.quantize(Decimal("0.01"))),
        "collection_rate": round(rate, 1),
        "arrears": str(arrears.quantize(Decimal("0.01"))),
        "active_tenants": leases.count(),
        "active_leases": leases.count(),
        "units": total_units,
        "occupied_units": occupied,
        "occupancy_rate": round((occupied / total_units) * 100, 1) if total_units else 0.0,
        "status_counts": status_counts,
        "unmatched_payments": unmatched,
        "open_promises": promises,
    }


def overdue_tenants(organization, *, status_filter=None, property_id=None, bucket=None) -> list[dict]:
    from apps.leases.models import Lease

    leases = Lease.objects.filter(
        organization=organization, status=Lease.Status.ACTIVE
    ).select_related("tenant", "unit", "unit__property")
    if property_id:
        leases = leases.filter(unit__property_id=property_id)

    promises = {
        promise.lease_id: promise
        for promise in PromiseToPay.objects.filter(
            organization=organization, status=PromiseToPay.Status.OPEN
        ).order_by("promised_date")
    }
    rows = []
    for lease in leases:
        balance = lease_balance(lease)
        if balance <= ZERO:
            continue
        ageing = lease_ageing(lease)
        status = ageing["status"]
        if status_filter and status != status_filter.upper():
            continue
        if bucket and bucket not in ageing["buckets"]:
            continue
        promise = promises.get(lease.id)
        rows.append(
            {
                "lease_id": str(lease.id),
                "tenant_id": str(lease.tenant_id),
                "tenant": lease.tenant.full_name,
                "phone": lease.tenant.phone,
                "property": lease.unit.property.name,
                "unit": lease.unit.code,
                "rent": str(lease.rent_amount),
                "balance": str(balance),
                "status": status,
                "days_overdue": ageing["days_overdue"],
                "buckets": {key: str(value) for key, value in ageing["buckets"].items()},
                "promise": (
                    {
                        "amount": str(promise.amount),
                        "date": promise.promised_date.isoformat(),
                        "note": promise.note,
                    }
                    if promise
                    else None
                ),
            }
        )
    rows.sort(key=lambda row: (-row["days_overdue"], row["tenant"]))
    return rows


def expected_vs_collected(organization, months=12, property_id=None) -> list[dict]:
    today = timezone.localdate().replace(day=1)
    rows = []
    for offset in range(months - 1, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        start = date(year, month, 1)
        _, end = month_bounds(start)
        ledger = LedgerEntry.objects.filter(organization=organization)
        if property_id:
            ledger = ledger.filter(unit__property_id=property_id)
        rent = (
            ledger.filter(entry_type=LedgerEntry.Type.RENT_CHARGE, period_start=start).aggregate(
                total=Sum("amount")
            )["total"]
            or ZERO
        )
        fees = (
            ledger.filter(
                entry_type=LedgerEntry.Type.LATE_FEE,
                effective_date__gte=start,
                effective_date__lte=end,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        paid = -(
            ledger.filter(
                entry_type=LedgerEntry.Type.PAYMENT,
                effective_date__gte=start,
                effective_date__lte=end,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        expected = rent + fees
        rows.append(
            {
                "month": f"{start:%Y-%m}",
                "expected": str(expected.quantize(Decimal("0.01"))),
                "collected": str(paid.quantize(Decimal("0.01"))),
                "difference": str((paid - expected).quantize(Decimal("0.01"))),
                "rate": round(float(paid / expected * 100), 1) if expected > 0 else 0.0,
            }
        )
    return rows


def property_income(organization, start=None, end=None) -> list[dict]:
    from apps.properties.models import Property

    start = date.fromisoformat(start) if start else timezone.localdate().replace(day=1)
    end = date.fromisoformat(end) if end else timezone.localdate()
    rows = []
    for prop in Property.objects.filter(organization=organization).order_by("name"):
        ledger = LedgerEntry.objects.filter(organization=organization, unit__property=prop)
        rent = (
            ledger.filter(
                entry_type=LedgerEntry.Type.RENT_CHARGE,
                effective_date__gte=start,
                effective_date__lte=end,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        fees = (
            ledger.filter(
                entry_type=LedgerEntry.Type.LATE_FEE,
                effective_date__gte=start,
                effective_date__lte=end,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        paid = -(
            ledger.filter(
                entry_type=LedgerEntry.Type.PAYMENT,
                effective_date__gte=start,
                effective_date__lte=end,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        rows.append(
            {
                "property_id": str(prop.id),
                "property": prop.name,
                "expected": str((rent + fees).quantize(Decimal("0.01"))),
                "collected": str(paid.quantize(Decimal("0.01"))),
                "difference": str((paid - rent - fees).quantize(Decimal("0.01"))),
            }
        )
    return rows


def occupancy(organization) -> list[dict]:
    from apps.properties.models import Property, Unit

    rows = []
    for prop in Property.objects.filter(organization=organization).order_by("name"):
        units = Unit.objects.filter(property=prop, deleted_at__isnull=True)
        total = units.count()
        occupied = units.filter(status=Unit.Status.OCCUPIED).count()
        rows.append(
            {
                "property_id": str(prop.id),
                "property": prop.name,
                "units": total,
                "occupied": occupied,
                "vacant": units.filter(status=Unit.Status.VACANT).count(),
                "maintenance": units.filter(status=Unit.Status.MAINTENANCE).count(),
                "occupancy_rate": round((occupied / total) * 100, 1) if total else 0.0,
            }
        )
    return rows


def arrears_ageing(organization) -> dict:
    from apps.leases.models import Lease

    totals = {bucket: ZERO for bucket in BUCKETS}
    by_property = defaultdict(lambda: {bucket: ZERO for bucket in BUCKETS})
    leases = Lease.objects.filter(
        organization=organization, status=Lease.Status.ACTIVE
    ).select_related("tenant", "unit", "unit__property")
    for lease in leases:
        ageing = lease_ageing(lease)
        for bucket, value in ageing["buckets"].items():
            totals[bucket] = totals.get(bucket, ZERO) + value
            by_property[lease.unit.property.name][bucket] += value
    return {
        "totals": {key: str(value.quantize(Decimal("0.01"))) for key, value in totals.items()},
        "by_property": {
            prop: {key: str(value.quantize(Decimal("0.01"))) for key, value in buckets.items()}
            for prop, buckets in by_property.items()
        },
        "total_outstanding": str(sum(totals.values(), ZERO).quantize(Decimal("0.01"))),
    }


def report_table(organization, report_type: str, params: dict) -> tuple[str, list[str], list[list]]:
    if report_type == "expected-vs-collected":
        rows = expected_vs_collected(
            organization,
            months=int(params.get("months", 12)),
            property_id=params.get("property"),
        )
        headers = ["Month", "Expected", "Collected", "Difference", "Rate %"]
        return "Expected vs collected", headers, [
            [r["month"], r["expected"], r["collected"], r["difference"], r["rate"]] for r in rows
        ]
    if report_type == "property-income":
        rows = property_income(organization, params.get("from"), params.get("to"))
        headers = ["Property", "Expected", "Collected", "Difference"]
        return "Property income", headers, [
            [r["property"], r["expected"], r["collected"], r["difference"]] for r in rows
        ]
    if report_type == "occupancy":
        rows = occupancy(organization)
        headers = ["Property", "Units", "Occupied", "Vacant", "Maintenance", "Rate %"]
        return "Occupancy", headers, [
            [r["property"], r["units"], r["occupied"], r["vacant"], r["maintenance"], r["occupancy_rate"]]
            for r in rows
        ]
    if report_type == "arrears-ageing":
        data = arrears_ageing(organization)
        headers = ["Bucket", "Amount"]
        rows = [[key, value] for key, value in data["totals"].items()]
        rows.append(["Total", data["total_outstanding"]])
        return "Arrears ageing", headers, rows
    if report_type == "overdue":
        rows = overdue_tenants(
            organization,
            status_filter=params.get("status"),
            property_id=params.get("property"),
            bucket=params.get("bucket"),
        )
        headers = ["Tenant", "Phone", "Property", "Unit", "Balance", "Days overdue", "Status"]
        return "Overdue tenants", headers, [
            [r["tenant"], r["phone"], r["property"], r["unit"], r["balance"], r["days_overdue"], r["status"]]
            for r in rows
        ]
    raise ValueError(f"Unknown report type: {report_type}")
