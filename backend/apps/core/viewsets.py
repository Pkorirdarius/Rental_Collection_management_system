from rest_framework import viewsets

from apps.core.audit import audit
from apps.core.models import AuditLog


class AuditedModelViewSet(viewsets.ModelViewSet):
    """Adds immutable audit records around standard CRUD operations."""

    def perform_create(self, serializer):
        obj = serializer.save()
        audit(AuditLog.Action.CREATE, obj=obj)
        return obj

    def perform_update(self, serializer):
        obj = serializer.save()
        audit(AuditLog.Action.UPDATE, obj=obj, changes=serializer.validated_data)
        return obj

    def perform_destroy(self, instance):
        if hasattr(instance, "deleted_at"):
            instance.delete(deleted_by=self.request.user)
        else:
            instance.delete()
        audit(AuditLog.Action.DELETE, obj=instance)
