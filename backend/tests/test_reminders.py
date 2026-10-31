from datetime import date

import pytest

from apps.ledger.services import generate_rent_charges
from apps.notifications.models import Reminder, ReminderSetting
from apps.notifications.services import build_reminders, send_reminder


@pytest.mark.django_db
def test_reminder_cadence_pre_due_due_and_overdue(org, lease):
    generate_rent_charges(2026, 10, org)

    pre_due = build_reminders(org, today=date(2026, 10, 2))
    assert [reminder.reminder_type for reminder in pre_due] == [Reminder.Type.PRE_DUE]
    assert "due on 05 Oct 2026" in pre_due[0].message

    due = build_reminders(org, today=date(2026, 10, 5))
    assert [reminder.reminder_type for reminder in due] == [Reminder.Type.DUE]

    overdue = build_reminders(org, today=date(2026, 10, 6))
    assert [reminder.reminder_type for reminder in overdue] == [Reminder.Type.OVERDUE_1]

    assert Reminder.objects.count() == 3


@pytest.mark.django_db
def test_reminder_builder_is_idempotent(org, lease):
    generate_rent_charges(2026, 10, org)
    first = build_reminders(org, today=date(2026, 10, 2))
    second = build_reminders(org, today=date(2026, 10, 2))
    assert len(first) == 1
    assert second == []
    assert Reminder.objects.count() == 1


@pytest.mark.django_db
def test_disabled_reminders_create_nothing(org, lease):
    generate_rent_charges(2026, 10, org)
    setting = ReminderSetting.get_for_org(org)
    setting.enabled = False
    setting.save(update_fields=["enabled"])
    assert build_reminders(org, today=date(2026, 10, 2)) == []


@pytest.mark.django_db
def test_send_reminder_skips_when_sms_not_configured(org, lease):
    generate_rent_charges(2026, 10, org)
    reminder = build_reminders(org, today=date(2026, 10, 2))[0]
    result = send_reminder(reminder)
    assert result.status == Reminder.Status.SKIPPED
    assert "not configured" in result.error
