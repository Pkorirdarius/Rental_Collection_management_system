from celery import shared_task

from apps.notifications.services import retry_failed_messages, send_pending_reminders


@shared_task
def send_rent_reminders_task():
    return send_pending_reminders()


@shared_task
def retry_failed_sms_task():
    return retry_failed_messages()
