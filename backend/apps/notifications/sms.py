import logging
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.utils import timezone

from apps.accounts.utils import normalize_phone
from apps.notifications.models import MessageLog
from apps.notifications.templates import render

logger = logging.getLogger(__name__)


def send_sms(
    *,
    organization,
    phone,
    message,
    tenant=None,
    template="",
    reminder=None,
    payment=None,
) -> MessageLog:
    log = MessageLog.objects.create(
        organization=organization,
        tenant=tenant,
        phone=normalize_phone(phone) or phone,
        channel="SMS",
        template=template,
        body=message[:480],
        reminder=reminder,
        payment=payment,
    )
    return deliver_message_log(log)


def deliver_message_log(log: MessageLog) -> MessageLog:
    config = settings.AFRICASTALKING
    if not config.get("ENABLED") or not config.get("USERNAME") or not config.get("API_KEY"):
        log.status = MessageLog.Status.SKIPPED
        log.error = "SMS provider not configured"
        log.save(update_fields=["status", "error", "updated_at"])
        return log

    sandbox = config["USERNAME"] == "sandbox"
    url = (
        "https://api.sandbox.africastalking.com/version1/messaging"
        if sandbox
        else "https://api.africastalking.com/version1/messaging"
    )
    data = {
        "username": config["USERNAME"],
        "to": log.phone,
        "message": log.body,
    }
    if config.get("SENDER_ID"):
        data["from"] = config["SENDER_ID"]

    try:
        response = requests.post(
            url,
            data=data,
            headers={"apiKey": config["API_KEY"], "Accept": "application/json"},
            timeout=20,
        )
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 - messaging must not break business flows
        log.status = MessageLog.Status.FAILED
        log.error = str(exc)[:500]
        log.retry_count += 1
        log.save(update_fields=["status", "error", "retry_count", "updated_at"])
        logger.warning("SMS delivery failed: %s", exc)
        return log

    log.provider_response = payload
    recipients = (payload.get("SMSMessageData") or {}).get("Recipients") or []
    if response.status_code < 300 and recipients:
        recipient = recipients[0]
        status = str(recipient.get("status", ""))
        log.provider_message_id = str(recipient.get("messageId", ""))
        log.cost = _parse_cost(recipient.get("cost"))
        if status.lower() in {"success", "sent"}:
            log.status = MessageLog.Status.SENT
            log.sent_at = timezone.now()
        else:
            log.status = MessageLog.Status.FAILED
            log.error = status[:500]
            log.retry_count += 1
    else:
        log.status = MessageLog.Status.FAILED
        log.error = str(payload)[:500]
        log.retry_count += 1
    log.save(
        update_fields=[
            "provider_response",
            "provider_message_id",
            "cost",
            "status",
            "error",
            "retry_count",
            "sent_at",
            "updated_at",
        ]
    )
    return log


def _parse_cost(value) -> Decimal:
    if not value:
        return Decimal("0.0000")
    text = str(value).replace("KES", "").replace("Ksh", "").strip()
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0.0000")


def send_payment_receipt_sms(payment, receipt) -> MessageLog | None:
    tenant = payment.tenant
    if tenant is None or not tenant.phone:
        return None
    from apps.ledger.services import lease_balance
    from apps.notifications.models import ReminderSetting

    setting = ReminderSetting.get_for_org(payment.organization)
    lease = payment.lease
    balance = lease_balance(lease) if lease else payment.amount
    message = render(
        setting.language,
        "receipt",
        name=tenant.full_name.split(" ")[0],
        amount=payment.amount,
        property=lease.unit.property.name if lease else "",
        unit=lease.unit.code if lease else "",
        receipt=receipt.number,
        balance=balance,
    )
    log = send_sms(
        organization=payment.organization,
        phone=tenant.phone,
        message=message,
        tenant=tenant,
        template="receipt",
        payment=payment,
    )
    if log.status == MessageLog.Status.SENT:
        receipt.sms_sent = True
        receipt.save(update_fields=["sms_sent", "updated_at"])
    return log


def send_reminder_sms(reminder) -> MessageLog:
    from apps.notifications.models import ReminderSetting

    setting = ReminderSetting.get_for_org(reminder.organization)
    lease = reminder.lease
    key = "overdue" if reminder.reminder_type.startswith("OVERDUE") else (
        "due" if reminder.reminder_type == reminder.Type.DUE else "pre_due"
    )
    message = render(
        setting.language,
        key,
        name=reminder.tenant.full_name.split(" ")[0],
        amount=reminder.amount_due,
        unit=lease.unit.code,
        property=lease.unit.property.name,
        due_date=lease.due_date_for(reminder.scheduled_for.replace(day=1)).strftime("%d %b %Y"),
        days=reminder.days_overdue,
        shortcode=reminder.organization.mpesa_shortcode or "your paybill",
        bill_ref=lease.unit.mpesa_bill_ref,
    )
    return send_sms(
        organization=reminder.organization,
        phone=reminder.tenant.phone,
        message=message,
        tenant=reminder.tenant,
        template=f"reminder_{key}",
        reminder=reminder,
    )
