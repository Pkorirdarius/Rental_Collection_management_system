import logging
from datetime import date, timedelta

from django.utils import timezone

from apps.core.audit import audit
from apps.core.models import AuditLog
from apps.ledger.services import days_overdue, lease_balance
from apps.notifications.models import MessageLog, Reminder, ReminderSetting
from apps.notifications.sms import send_reminder_sms
from apps.notifications.templates import render

logger = logging.getLogger(__name__)


def build_reminders(organization, today: date | None = None) -> list[Reminder]:
    from apps.leases.models import Lease

    today = today or timezone.localdate()
    setting = ReminderSetting.get_for_org(organization)
    if not setting.enabled:
        return []
    period_start = today.replace(day=1)
    offsets = {int(value) for value in (setting.escalation_offsets or [1, 3, 7, 14, 30])}
    leases = Lease.objects.filter(
        organization=organization, status=Lease.Status.ACTIVE
    ).select_related("tenant", "unit", "unit__property")

    created: list[Reminder] = []
    for lease in leases:
        balance = lease_balance(lease)
        if balance <= 0:
            continue
        due = lease.due_date_for(period_start)
        delta = (due - today).days
        reminder_type = None
        if delta == setting.pre_due_days:
            reminder_type = Reminder.Type.PRE_DUE
        elif delta == 0:
            reminder_type = Reminder.Type.DUE
        elif delta < 0:
            days_since_due = -delta
            if days_since_due in offsets:
                reminder_type = f"OVERDUE_{days_since_due}"
        if reminder_type is None:
            continue

        key = f"{period_start:%Y-%m}"
        if reminder_type.startswith("OVERDUE"):
            key = f"{period_start:%Y-%m}-{reminder_type}"
        overdue = days_overdue(lease, today)
        message = render(
            setting.language,
            "overdue" if reminder_type.startswith("OVERDUE") else (
                "due" if reminder_type == Reminder.Type.DUE else "pre_due"
            ),
            name=lease.tenant.full_name.split(" ")[0],
            amount=balance,
            unit=lease.unit.code,
            property=lease.unit.property.name,
            due_date=due.strftime("%d %b %Y"),
            days=overdue,
            shortcode=organization.mpesa_shortcode or "your paybill",
            bill_ref=lease.unit.mpesa_bill_ref,
        )
        reminder, was_created = Reminder.objects.get_or_create(
            lease=lease,
            reminder_type=reminder_type,
            period_key=key,
            defaults={
                "organization": organization,
                "tenant": lease.tenant,
                "scheduled_for": today,
                "amount_due": balance,
                "days_overdue": overdue,
                "message": message,
            },
        )
        if was_created:
            created.append(reminder)
    return created


def send_reminder(reminder: Reminder, actor=None) -> Reminder:
    if reminder.status == Reminder.Status.SENT:
        return reminder
    log = send_reminder_sms(reminder)
    if log.status == MessageLog.Status.SENT:
        reminder.status = Reminder.Status.SENT
        reminder.sent_at = timezone.now()
        reminder.error = ""
    elif log.status == MessageLog.Status.SKIPPED:
        reminder.status = Reminder.Status.SKIPPED
        reminder.error = log.error
    else:
        reminder.status = Reminder.Status.FAILED
        reminder.error = log.error[:255]
    reminder.save(update_fields=["status", "sent_at", "error", "updated_at"])
    audit(
        AuditLog.Action.REMINDER_SENT,
        obj=reminder,
        changes={"status": reminder.status, "type": reminder.reminder_type},
    )
    return reminder


def send_pending_reminders(today: date | None = None) -> dict:
    today = today or timezone.localdate()
    from apps.core.models import Organization

    created = sent = failed = 0
    for organization in Organization.objects.filter(is_active=True):
        reminders = build_reminders(organization, today)
        created += len(reminders)
        pending = Reminder.objects.filter(
            organization=organization,
            status=Reminder.Status.PENDING,
            scheduled_for__lte=today,
        )
        for reminder in pending:
            result = send_reminder(reminder)
            if result.status == Reminder.Status.SENT:
                sent += 1
            elif result.status == Reminder.Status.FAILED:
                failed += 1
    return {"created": created, "sent": sent, "failed": failed, "date": today.isoformat()}


def create_manual_reminder(lease, *, actor=None, message="") -> Reminder:
    balance = lease_balance(lease)
    reminder = Reminder.objects.create(
        organization=lease.organization,
        lease=lease,
        tenant=lease.tenant,
        reminder_type=Reminder.Type.MANUAL,
        period_key=f"{timezone.localdate():%Y-%m-%d}-{timezone.now():%H%M%S}",
        scheduled_for=timezone.localdate(),
        amount_due=balance,
        days_overdue=days_overdue(lease),
        message=message[:480],
        created_by=actor,
    )
    return send_reminder(reminder, actor=actor)


def retry_failed_messages(limit=100) -> dict:
    from apps.notifications.sms import deliver_message_log

    cutoff = timezone.now() - timedelta(days=2)
    logs = MessageLog.objects.filter(
        status=MessageLog.Status.FAILED, retry_count__lt=3, created_at__gte=cutoff
    )[:limit]
    retried = delivered = 0
    for log in logs:
        retried += 1
        result = deliver_message_log(log)
        if result.status == MessageLog.Status.SENT:
            delivered += 1
    return {"retried": retried, "delivered": delivered}
