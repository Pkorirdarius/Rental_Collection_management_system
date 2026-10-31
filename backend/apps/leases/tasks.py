from celery import shared_task
from django.utils import timezone

from apps.core.audit import audit
from apps.core.models import AuditLog
from apps.leases.models import Lease
from apps.properties.models import Unit


@shared_task
def expire_leases_task():
    today = timezone.localdate()
    expired = Lease.objects.filter(
        status=Lease.Status.ACTIVE, end_date__lt=today
    ).select_related("unit")
    count = 0
    for lease in expired:
        lease.status = Lease.Status.ENDED
        lease.save(update_fields=["status", "updated_at"])
        if not Lease.objects.filter(unit=lease.unit, status=Lease.Status.ACTIVE).exists():
            Unit.objects.filter(pk=lease.unit_id).update(status=Unit.Status.VACANT)
        audit(
            AuditLog.Action.UPDATE,
            obj=lease,
            organization=lease.organization,
            changes={"status": "ENDED", "reason": "lease end date reached"},
        )
        count += 1
    return {"expired": count}
