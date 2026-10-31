from celery import shared_task
from django.utils import timezone

from apps.ledger.services import apply_late_fees, generate_rent_charges


@shared_task
def generate_rent_charges_task(year=None, month=None):
    today = timezone.localdate()
    return generate_rent_charges(year or today.year, month or today.month)


@shared_task
def apply_late_fees_task():
    return apply_late_fees()
