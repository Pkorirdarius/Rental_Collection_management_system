import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.utils import normalize_phone
from apps.core.audit import audit
from apps.core.models import AuditLog, Organization
from apps.ledger.models import LedgerEntry
from apps.ledger.services import post_payment, post_reversal
from apps.payments.daraja import DarajaClient, DarajaError
from apps.payments.models import (
    MpesaRequest,
    Payment,
    PaymentEvent,
    Receipt,
    ReceiptSequence,
    ReconciliationRun,
)
from apps.payments.receipts import build_receipt_pdf
from apps.properties.models import Unit

logger = logging.getLogger(__name__)
NAIROBI = ZoneInfo("Africa/Nairobi")
ZERO = Decimal("0.00")


def _decimal(value, field="amount") -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid {field}")
    if amount <= ZERO:
        raise ValueError(f"{field} must be greater than zero")
    return amount


def next_receipt_number(organization, year=None) -> str:
    year = year or timezone.localdate().year
    with transaction.atomic():
        sequence, _ = ReceiptSequence.objects.select_for_update().get_or_create(
            organization=organization, year=year
        )
        sequence.last_number += 1
        sequence.save(update_fields=["last_number"])
    prefix = organization.slug.upper()[:10]
    return f"RCPT-{prefix}-{year}-{sequence.last_number:06d}"


def issue_receipt(payment, *, issued_by=None, number=None) -> Receipt:
    existing = getattr(payment, "receipt", None)
    if existing:
        return existing
    receipt = Receipt.objects.create(
        organization=payment.organization,
        payment=payment,
        number=number or next_receipt_number(payment.organization),
        issued_by=issued_by,
    )
    try:
        pdf = build_receipt_pdf(payment, receipt)
        receipt.pdf_file.save(f"{receipt.number}.pdf", ContentFile(pdf), save=True)
    except Exception:  # pragma: no cover - PDF generation should not block a payment
        logger.exception("Failed to render receipt PDF for %s", receipt.number)
    PaymentEvent.objects.create(
        payment=payment,
        event="RECEIPT_ISSUED",
        detail={"receipt": receipt.number},
        actor=issued_by,
    )
    return receipt


def _notify_receipt(payment, receipt):
    from apps.notifications.services import send_payment_receipt_sms

    try:
        send_payment_receipt_sms(payment, receipt)
    except Exception:  # pragma: no cover - SMS failures must not break payments
        logger.exception("Receipt SMS failed for payment %s", payment.id)


def record_cash_payment(
    *,
    organization,
    tenant,
    lease=None,
    amount,
    paid_at=None,
    received_by=None,
    note="",
    photo=None,
    created_by=None,
    idempotency_key=None,
) -> tuple[Payment, Receipt]:
    if idempotency_key:
        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing, getattr(existing, "receipt", None)
    amount = _decimal(amount)
    lease = lease or tenant.active_lease
    if lease is None:
        raise ValueError("Tenant has no active lease; choose a lease explicitly.")
    if lease.tenant_id != tenant.id or lease.organization_id != organization.id:
        raise ValueError("Lease does not belong to this tenant and organization.")

    paid_at = paid_at or timezone.now()
    with transaction.atomic():
        number = next_receipt_number(organization)
        payment = Payment.objects.create(
            organization=organization,
            tenant=tenant,
            lease=lease,
            unit=lease.unit,
            method=Payment.Method.CASH,
            amount=amount,
            status=Payment.Status.CONFIRMED,
            paid_at=paid_at,
            reference=number,
            received_by=received_by,
            notes=note,
            photo=photo,
            idempotency_key=idempotency_key,
        )
        post_payment(
            lease,
            amount=amount,
            payment=payment,
            effective_date=timezone.localtime(paid_at).date(),
            source=LedgerEntry.Source.CASH,
            description=f"Cash payment {number}",
            created_by=created_by or received_by,
        )
        receipt = issue_receipt(payment, issued_by=created_by or received_by, number=number)
        PaymentEvent.objects.create(
            payment=payment, event="CASH_RECORDED", detail={"receipt": number}, actor=created_by
        )
    audit(
        AuditLog.Action.PAYMENT_RECORDED,
        obj=payment,
        changes={"amount": str(amount), "method": "CASH", "receipt": number},
    )
    transaction.on_commit(lambda: _notify_receipt(payment, receipt))
    return payment, receipt


def reverse_payment(payment: Payment, *, reason="", actor=None) -> list[LedgerEntry]:
    if payment.status == Payment.Status.REVERSED:
        raise ValueError("Payment is already reversed.")
    if payment.status != Payment.Status.CONFIRMED:
        raise ValueError("Only confirmed payments can be reversed.")
    entries = list(
        payment.ledger_entries.filter(entry_type=LedgerEntry.Type.PAYMENT).prefetch_related("reversals")
    )
    if not entries:
        raise ValueError("Payment has no ledger entries to reverse.")
    reversals = []
    with transaction.atomic():
        for entry in entries:
            if entry.reversals.exists():
                continue
            reversal, _ = post_reversal(entry, reason=reason, created_by=actor)
            reversals.append(reversal)
        payment.status = Payment.Status.REVERSED
        payment.match_note = reason[:255]
        payment.save(update_fields=["status", "match_note", "updated_at"])
        PaymentEvent.objects.create(
            payment=payment, event="REVERSED", detail={"reason": reason}, actor=actor
        )
    audit(
        AuditLog.Action.PAYMENT_REVERSED,
        obj=payment,
        changes={"reason": reason, "reversals": [str(r.id) for r in reversals]},
    )
    return reversals


def match_payment(payment: Payment, *, lease, actor=None, note="") -> Payment:
    if payment.status not in {Payment.Status.UNMATCHED, Payment.Status.PENDING}:
        raise ValueError("Only unmatched or pending payments can be manually matched.")
    if payment.organization_id != lease.organization_id:
        raise ValueError("Payment and lease belong to different organizations.")
    with transaction.atomic():
        payment.lease = lease
        payment.tenant = lease.tenant
        payment.unit = lease.unit
        payment.status = Payment.Status.CONFIRMED
        payment.matched_by = actor
        payment.matched_at = timezone.now()
        payment.match_note = note[:255]
        payment.save(
            update_fields=[
                "lease",
                "tenant",
                "unit",
                "status",
                "matched_by",
                "matched_at",
                "match_note",
                "updated_at",
            ]
        )
        post_payment(
            lease,
            amount=payment.amount,
            payment=payment,
            effective_date=timezone.localtime(payment.paid_at).date(),
            source=LedgerEntry.Source.MPESA if payment.is_mpesa else LedgerEntry.Source.CASH,
            description=f"Matched payment {payment.reference}",
            created_by=actor,
        )
        receipt = issue_receipt(payment, issued_by=actor)
        PaymentEvent.objects.create(
            payment=payment, event="MATCHED", detail={"lease": str(lease.id), "note": note}, actor=actor
        )
    audit(
        AuditLog.Action.PAYMENT_MATCHED,
        obj=payment,
        changes={"lease": str(lease.id), "note": note},
    )
    transaction.on_commit(lambda: _notify_receipt(payment, receipt))
    return payment


def _parse_mpesa_time(value) -> datetime:
    if value:
        try:
            parsed = datetime.strptime(str(value), "%Y%m%d%H%M%S")
            return timezone.make_aware(parsed, NAIROBI)
        except ValueError:
            pass
    return timezone.now()


def _organization_for_shortcode(shortcode: str):
    shortcode = str(shortcode or "").strip()
    if shortcode:
        org = Organization.objects.filter(mpesa_shortcode=shortcode, is_active=True).first()
        if org:
            return org
        from apps.properties.models import Property

        prop = Property.objects.filter(
            mpesa_shortcode_override=shortcode, is_active=True
        ).select_related("organization").first()
        if prop:
            return prop.organization
    return Organization.objects.filter(is_active=True).order_by("created_at").first()


def _shortcode_is_valid(organization, shortcode, unit=None) -> bool:
    configured = {organization.mpesa_shortcode}
    if unit is not None:
        configured.add(unit.property.mpesa_shortcode_override)
    configured = {value for value in configured if value}
    if not configured:
        return True
    return str(shortcode) in configured


def _find_lease_for_c2b(organization, bill_ref, phone):
    from apps.leases.models import Lease
    from apps.tenants.models import Tenant

    normalized = (bill_ref or "").replace(" ", "").upper()
    if normalized:
        unit = Unit.objects.filter(
            organization=organization, mpesa_bill_ref__iexact=normalized
        ).select_related("property").first()
        if unit:
            lease = Lease.objects.filter(unit=unit, status=Lease.Status.ACTIVE).select_related(
                "tenant", "unit", "unit__property"
            ).first()
            if lease:
                return lease, "bill_ref"

    phone = normalize_phone(phone)
    if phone:
        tenants = Tenant.objects.filter(organization=organization).filter(
            models_q_phone(phone)
        ).distinct()
        for tenant in tenants:
            active = list(
                tenant.leases.filter(status=Lease.Status.ACTIVE).select_related(
                    "tenant", "unit", "unit__property"
                )[:2]
            )
            if len(active) == 1:
                return active[0], "phone"
    return None, ""


def models_q_phone(phone):
    from django.db.models import Q

    return Q(phone=phone) | Q(alt_phone=phone)


def ingest_mpesa_payment(
    *,
    receipt: str,
    amount,
    phone: str,
    bill_ref: str = "",
    shortcode: str = "",
    paid_at=None,
    raw_payload=None,
    method=Payment.Method.MPESA_C2B,
    expected_lease=None,
    force_unmatched=False,
) -> tuple[Payment | None, bool]:
    receipt = str(receipt or "").strip().upper()
    if not receipt:
        raise ValueError("M-Pesa receipt number is required")
    amount = _decimal(amount, "M-Pesa amount")
    phone = normalize_phone(phone) or str(phone or "")
    organization = _organization_for_shortcode(shortcode)
    if organization is None:
        logger.error("M-Pesa payment %s received but no organization is configured", receipt)
        return None, False

    existing = Payment.objects.filter(organization=organization, reference=receipt).first()
    if existing:
        return existing, False

    lease = expected_lease
    match_source = "stk_request" if expected_lease else ""
    if lease is None and not force_unmatched:
        lease, match_source = _find_lease_for_c2b(organization, bill_ref, phone)
    shortcode_ok = _shortcode_is_valid(
        organization, shortcode, unit=lease.unit if lease else None
    )
    if not shortcode_ok:
        force_unmatched = True

    status = (
        Payment.Status.CONFIRMED
        if lease is not None and not force_unmatched
        else Payment.Status.UNMATCHED
    )
    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                organization=organization,
                tenant=lease.tenant if lease else None,
                lease=lease,
                unit=lease.unit if lease else None,
                method=method,
                amount=amount,
                status=status,
                paid_at=paid_at or timezone.now(),
                reference=receipt,
                provider_txn_id=receipt,
                phone=phone,
                bill_ref=(bill_ref or "")[:30],
                raw_payload=raw_payload or {},
                match_note=(
                    f"Matched by {match_source}"
                    if status == Payment.Status.CONFIRMED
                    else "Awaiting manual assignment"
                ),
            )
            PaymentEvent.objects.create(
                payment=payment,
                event="MPESA_RECEIVED",
                detail={"match_source": match_source, "shortcode_ok": shortcode_ok},
            )
            if status == Payment.Status.CONFIRMED:
                post_payment(
                    lease,
                    amount=amount,
                    payment=payment,
                    effective_date=timezone.localtime(payment.paid_at).date(),
                    source=LedgerEntry.Source.MPESA,
                    description=f"M-Pesa {receipt}",
                )
                issue_receipt(payment)
    except IntegrityError:
        existing = Payment.objects.filter(organization=organization, reference=receipt).first()
        return existing, False

    audit(
        AuditLog.Action.MPESA_CALLBACK,
        obj=payment,
        changes={"receipt": receipt, "status": status, "match_source": match_source},
    )
    if status == Payment.Status.CONFIRMED:
        receipt_obj = payment.receipt
        transaction.on_commit(lambda: _notify_receipt(payment, receipt_obj))
    return payment, True


def request_stk_push(
    *,
    lease,
    phone=None,
    amount=None,
    actor=None,
    purpose=MpesaRequest.Purpose.PAY_NOW,
) -> MpesaRequest:
    phone = normalize_phone(phone or lease.tenant.phone)
    if not phone:
        raise ValueError("A valid phone number is required")
    amount = _decimal(amount or lease.rent_amount)
    if not str(phone).startswith("254"):
        raise ValueError("Phone number must be a Kenyan number in 2547XXXXXXXX format")

    base = settings.MPESA.get("CALLBACK_BASE_URL", "").rstrip("/")
    token = settings.MPESA.get("CALLBACK_TOKEN", "")
    if not base:
        raise DarajaError("MPESA_CALLBACK_BASE_URL is not configured.")
    callback_url = f"{base}/api/v1/webhooks/mpesa/stk/callback?token={token}"

    request = MpesaRequest.objects.create(
        organization=lease.organization,
        tenant=lease.tenant,
        lease=lease,
        phone=phone,
        amount=amount,
        purpose=purpose,
        checkout_request_id=f"pending-{uuid.uuid4()}",
        initiated_by=actor,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    client = DarajaClient()
    try:
        response = client.stk_push(
            phone=phone,
            amount=int(amount),
            account_reference=lease.unit.mpesa_bill_ref,
            description=f"Rent {lease.unit.code}",
            callback_url=callback_url,
        )
    except Exception as exc:
        request.status = MpesaRequest.Status.FAILED
        request.result_desc = str(exc)[:255]
        request.save(update_fields=["status", "result_desc", "updated_at"])
        audit(
            AuditLog.Action.STK_PUSH,
            obj=request,
            changes={"status": "FAILED", "error": str(exc)[:255]},
        )
        raise

    request.merchant_request_id = response.get("MerchantRequestID", "")
    request.checkout_request_id = response.get("CheckoutRequestID") or request.checkout_request_id
    request.raw_response = response
    if str(response.get("ResponseCode")) != "0":
        request.status = MpesaRequest.Status.FAILED
        request.result_desc = response.get("ResponseDescription", "")[:255]
    request.save(
        update_fields=[
            "merchant_request_id",
            "checkout_request_id",
            "raw_response",
            "status",
            "result_desc",
            "updated_at",
        ]
    )
    audit(
        AuditLog.Action.STK_PUSH,
        obj=request,
        changes={"status": request.status, "amount": str(amount), "phone": phone},
    )
    return request


def _metadata_dict(callback_metadata) -> dict:
    items = (callback_metadata or {}).get("Item") or []
    return {item.get("Name"): item.get("Value") for item in items if isinstance(item, dict)}


def process_stk_callback(payload: dict) -> MpesaRequest | None:
    body = (payload or {}).get("Body", {}).get("stkCallback", {})
    checkout_id = body.get("CheckoutRequestID", "")
    result_code = str(body.get("ResultCode", ""))
    result_desc = body.get("ResultDesc", "")
    request = MpesaRequest.objects.filter(checkout_request_id=checkout_id).first()
    metadata = _metadata_dict(body.get("CallbackMetadata"))
    mpesa_receipt = str(metadata.get("MpesaReceiptNumber") or "").strip().upper()

    if request is None:
        if result_code == "0" and mpesa_receipt:
            ingest_mpesa_payment(
                receipt=mpesa_receipt,
                amount=metadata.get("Amount", 0),
                phone=metadata.get("PhoneNumber", ""),
                paid_at=_parse_mpesa_time(metadata.get("TransactionDate")),
                raw_payload=payload,
                method=Payment.Method.MPESA_STK,
                force_unmatched=True,
            )
        return None

    request.result_code = result_code[:10]
    request.result_desc = result_desc[:255]
    request.raw_response = payload

    if result_code != "0":
        request.status = (
            MpesaRequest.Status.CANCELLED if result_code == "1037" else MpesaRequest.Status.FAILED
        )
        request.save(
            update_fields=["status", "result_code", "result_desc", "raw_response", "updated_at"]
        )
        return request

    if not mpesa_receipt:
        request.result_desc = "Success reported without receipt metadata; awaiting reconciliation."
        request.save(update_fields=["result_code", "result_desc", "raw_response", "updated_at"])
        return request

    amount = metadata.get("Amount", 0)
    try:
        callback_amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        callback_amount = ZERO

    force_unmatched = callback_amount != request.amount
    payment, _ = ingest_mpesa_payment(
        receipt=mpesa_receipt,
        amount=amount or request.amount,
        phone=metadata.get("PhoneNumber") or request.phone,
        bill_ref=request.lease.unit.mpesa_bill_ref if request.lease else "",
        shortcode=settings.MPESA.get("SHORTCODE", ""),
        paid_at=_parse_mpesa_time(metadata.get("TransactionDate")),
        raw_payload=payload,
        method=Payment.Method.MPESA_STK,
        expected_lease=request.lease,
        force_unmatched=force_unmatched,
    )
    request.mpesa_receipt = mpesa_receipt
    request.payment = payment
    if force_unmatched:
        request.status = MpesaRequest.Status.FAILED
        request.result_desc = "Amount did not match the STK request; payment queued as unmatched."
    else:
        request.status = MpesaRequest.Status.SUCCESS
    request.save(
        update_fields=[
            "status",
            "result_code",
            "result_desc",
            "mpesa_receipt",
            "payment",
            "raw_response",
            "updated_at",
        ]
    )
    return request


def reconcile_pending(organization=None) -> ReconciliationRun:
    from apps.payments.models import Payment

    run = ReconciliationRun.objects.create(organization=organization, started_at=timezone.now())
    now = timezone.now()
    requests = MpesaRequest.objects.filter(
        status=MpesaRequest.Status.PENDING,
        created_at__lt=now - timedelta(minutes=2),
    ).exclude(checkout_request_id__startswith="pending-")
    if organization:
        requests = requests.filter(organization=organization)

    client = DarajaClient()
    checked = matched = unmatched = errors = 0
    details = []
    for request in requests:
        checked += 1
        if request.created_at < now - timedelta(hours=24):
            request.status = MpesaRequest.Status.TIMEOUT
            request.result_desc = "No callback received within 24 hours."
            request.save(update_fields=["status", "result_desc", "updated_at"])
            details.append({"checkout": request.checkout_request_id, "result": "timeout"})
            continue
        try:
            response = client.stk_query(request.checkout_request_id)
            pseudo = {
                "Body": {
                    "stkCallback": {
                        "MerchantRequestID": response.get("MerchantRequestID", ""),
                        "CheckoutRequestID": request.checkout_request_id,
                        "ResultCode": response.get("ResultCode", ""),
                        "ResultDesc": response.get("ResultDesc", ""),
                        "CallbackMetadata": response.get("CallbackMetadata", {}),
                    }
                }
            }
            updated = process_stk_callback(pseudo)
            if updated and updated.status == MpesaRequest.Status.SUCCESS:
                matched += 1
            elif updated and updated.payment and updated.payment.status == Payment.Status.UNMATCHED:
                unmatched += 1
            details.append(
                {
                    "checkout": request.checkout_request_id,
                    "result": updated.status if updated else "missing",
                }
            )
        except Exception as exc:  # noqa: BLE001 - reconciliation must continue
            errors += 1
            logger.warning("Reconciliation failed for %s: %s", request.checkout_request_id, exc)
            details.append({"checkout": request.checkout_request_id, "error": str(exc)[:200]})

    unmatched += Payment.objects.filter(
        organization=organization, status=Payment.Status.UNMATCHED
    ).count() if organization else Payment.objects.filter(status=Payment.Status.UNMATCHED).count()

    run.finished_at = timezone.now()
    run.checked = checked
    run.matched = matched
    run.unmatched = unmatched
    run.errors = errors
    run.details = {"items": details}
    run.save(
        update_fields=["finished_at", "checked", "matched", "unmatched", "errors", "details", "updated_at"]
    )
    return run
