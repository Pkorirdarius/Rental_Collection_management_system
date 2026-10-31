import secrets

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.audit import audit
from apps.core.models import AuditLog
from apps.core.permissions import IsAdmin, IsAdminOrCaretaker
from apps.core.scoping import scope_tenant_record
from apps.core.viewsets import AuditedModelViewSet
from apps.tenants.models import Tenant
from apps.tenants.serializers import TenantPortalInviteSerializer, TenantSerializer


class TenantViewSet(AuditedModelViewSet):
    serializer_class = TenantSerializer
    search_fields = ["full_name", "phone", "email"]
    ordering_fields = ["full_name", "created_at"]
    filterset_fields = ["status"]

    def get_permissions(self):
        if self.action in {"list"}:
            return [IsAdminOrCaretaker()]
        if self.action in {"create", "update", "partial_update", "destroy", "portal_invite"}:
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return scope_tenant_record(
            Tenant.objects.select_related("user", "organization"), self.request.user
        )

    def perform_create(self, serializer):
        tenant = serializer.save()
        audit(AuditLog.Action.CREATE, obj=tenant)

    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        from apps.ledger.services import lease_balance, lease_status

        tenant = self.get_object()
        leases = tenant.leases.filter(status__in=["ACTIVE", "ENDED"]).select_related("unit__property")
        data = []
        for lease in leases:
            data.append(
                {
                    "lease_id": str(lease.id),
                    "unit": lease.unit.code,
                    "property": lease.unit.property.name,
                    "rent_amount": str(lease.rent_amount),
                    "balance": str(lease_balance(lease)),
                    "status": lease_status(lease),
                }
            )
        return Response({"tenant_id": str(tenant.id), "leases": data})

    @action(detail=True, methods=["get"])
    def statement(self, request, pk=None):
        from apps.ledger.services import tenant_statement

        tenant = self.get_object()
        return Response(tenant_statement(tenant))

    @action(detail=True, methods=["get"], url_path="statement.pdf")
    def statement_pdf(self, request, pk=None):
        from django.http import HttpResponse

        from apps.reports.exports import build_tenant_statement_pdf

        tenant = self.get_object()
        pdf = build_tenant_statement_pdf(tenant)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="statement-{tenant.id}.pdf"'
        return response

    @action(detail=True, methods=["post"], url_path="portal-invite")
    def portal_invite(self, request, pk=None):
        tenant = self.get_object()
        serializer = TenantPortalInviteSerializer(
            data=request.data, context={"request": request, "tenant": tenant}
        )
        serializer.is_valid(raise_exception=True)
        email = (serializer.validated_data.get("email") or tenant.email).lower()
        phone = serializer.validated_data.get("phone") or tenant.phone
        temp_password = secrets.token_urlsafe(9)

        with transaction.atomic():
            if User.objects.filter(email=email).exists():
                return Response(
                    {"detail": "A user with this email already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = User.objects.create_user(
                email=email,
                phone=phone,
                password=temp_password,
                full_name=tenant.full_name,
                role=User.Role.TENANT,
                organization=tenant.organization,
                must_change_password=True,
            )
            tenant.user = user
            tenant.email = email
            tenant.save(update_fields=["user", "email", "updated_at"])

        audit(
            AuditLog.Action.UPDATE,
            obj=tenant,
            changes={"portal_user_created": str(user.id)},
        )
        try:
            from apps.notifications.sms import send_sms

            send_sms(
                organization=tenant.organization,
                phone=phone,
                message=(
                    f"Your tenant portal is ready. Login with {email} and temporary "
                    f"password {temp_password}. Change it after signing in."
                ),
                tenant=tenant,
            )
        except Exception:  # pragma: no cover - SMS is best effort
            pass
        return Response(
            {
                "user_id": str(user.id),
                "email": email,
                "temporary_password": temp_password,
                "must_change_password": True,
            },
            status=status.HTTP_201_CREATED,
        )
