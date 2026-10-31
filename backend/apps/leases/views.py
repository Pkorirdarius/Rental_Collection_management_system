from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.audit import audit
from apps.core.models import AuditLog
from apps.core.permissions import IsAdmin
from apps.core.scoping import scope_lease_queryset
from apps.core.viewsets import AuditedModelViewSet
from apps.leases.models import Lease
from apps.leases.serializers import LeaseSerializer, LeaseTerminateSerializer


class LeaseViewSet(AuditedModelViewSet):
    serializer_class = LeaseSerializer
    search_fields = ["tenant__full_name", "tenant__phone", "unit__code", "unit__property__name"]
    ordering_fields = ["start_date", "created_at", "rent_amount"]
    filterset_fields = ["status", "unit", "tenant"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy", "terminate"}:
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Lease.objects.select_related(
            "tenant", "unit", "unit__property", "organization"
        )
        qs = scope_lease_queryset(qs, self.request.user)
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(unit__property_id=property_id)
        return qs

    def perform_create(self, serializer):
        lease = serializer.save()
        audit(AuditLog.Action.CREATE, obj=lease)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        lease = self.get_object()
        serializer = LeaseTerminateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lease)
        audit(
            AuditLog.Action.UPDATE,
            obj=lease,
            changes={"status": "TERMINATED", "reason": lease.termination_reason},
        )
        return Response(LeaseSerializer(lease, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        from apps.ledger.services import lease_balance, lease_status

        lease = self.get_object()
        return Response(
            {
                "lease_id": str(lease.id),
                "balance": str(lease_balance(lease)),
                "status": lease_status(lease),
            }
        )

    @action(detail=True, methods=["get"])
    def statement(self, request, pk=None):
        from apps.ledger.services import lease_statement

        lease = self.get_object()
        return Response(lease_statement(lease))
