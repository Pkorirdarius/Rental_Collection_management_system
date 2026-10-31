from celery import shared_task

from apps.payments.services import reconcile_pending


@shared_task
def reconcile_mpesa_task():
    run = reconcile_pending()
    return {
        "checked": run.checked,
        "matched": run.matched,
        "unmatched": run.unmatched,
        "errors": run.errors,
    }
