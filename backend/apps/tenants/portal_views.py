from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ledger.services import days_overdue, lease_balance, lease_status, tenant_statement
from apps.payments.models import MpesaRequest, Payment
from apps.payments.serializers import PaymentSerializer, STKPushSerializer
from apps.payments.services import request_stk_push
from apps.reports.exports import build_tenant_statement_pdf


def get_tenant(request):
    tenant = getattr(request.user, "tenant_profile", None)
    return tenant


class TenantOnlyMixin:
    permission_classes = [IsAuthenticated]

    def tenant_or_response(self, request):
        tenant = get_tenant(request)
        if tenant is None:
            return None, Response(
                {"detail": "No tenant profile is linked to this account."}, status=404
            )
        return tenant, None


class PortalProfileView(TenantOnlyMixin, APIView):
    def get(self, request):
        tenant, error = self.tenant_or_response(request)
        if error:
            return error
        lease = tenant.active_lease
        return Response(
            {
                "id": str(tenant.id),
                "full_name": tenant.full_name,
                "phone": tenant.phone,
                "email": tenant.email,
                "lease_id": str(lease.id) if lease else None,
                "property": lease.unit.property.name if lease else None,
                "unit": lease.unit.code if lease else None,
                "rent_amount": str(lease.rent_amount) if lease else None,
                "due_day": lease.due_day if lease else None,
                "balance": str(lease_balance(lease)) if lease else "0.00",
                "status": lease_status(lease) if lease else "INACTIVE",
                "days_overdue": days_overdue(lease) if lease else 0,
                "bill_ref": lease.unit.mpesa_bill_ref if lease else None,
            }
        )


class PortalBalanceView(TenantOnlyMixin, APIView):
    def get(self, request):
        tenant, error = self.tenant_or_response(request)
        if error:
            return error
        leases = tenant.leases.filter(status__in=["ACTIVE", "ENDED"]).select_related(
            "unit__property"
        )
        rows = [
            {
                "lease_id": str(lease.id),
                "property": lease.unit.property.name,
                "unit": lease.unit.code,
                "rent_amount": str(lease.rent_amount),
                "balance": str(lease_balance(lease)),
                "status": lease_status(lease),
                "days_overdue": days_overdue(lease),
            }
            for lease in leases
        ]
        return Response({"leases": rows})


class PortalPaymentsView(TenantOnlyMixin, APIView):
    def get(self, request):
        tenant, error = self.tenant_or_response(request)
        if error:
            return error
        payments = Payment.objects.filter(tenant=tenant).select_related(
            "lease", "unit", "unit__property", "receipt"
        )[:100]
        return Response(PaymentSerializer(payments, many=True).data)


class PortalReceiptsView(TenantOnlyMixin, APIView):
    def get(self, request):
        tenant, error = self.tenant_or_response(request)
        if error:
            return error
        payments = Payment.objects.filter(
            tenant=tenant, status=Payment.Status.CONFIRMED, receipt__isnull=False
        ).select_related("receipt")[:100]
        return Response(
            [
                {
                    "payment_id": str(payment.id),
                    "receipt_number": payment.receipt.number,
                    "amount": str(payment.amount),
                    "paid_at": payment.paid_at,
                    "download": f"/api/v1/payments/{payment.id}/receipt.pdf",
                }
                for payment in payments
            ]
        )


class PortalStatementView(TenantOnlyMixin, APIView):
    def get(self, request):
        tenant, error = self.tenant_or_response(request)
        if error:
            return error
        if request.query_params.get("format") == "pdf":
            pdf = build_tenant_statement_pdf(tenant)
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="statement-{tenant.id}.pdf"'
            return response
        return Response(tenant_statement(tenant))


class PortalPayView(TenantOnlyMixin, APIView):
    throttle_scope = "mpesa"

    def post(self, request):
        tenant, error = self.tenant_or_response(request)
        if error:
            return error
        serializer = STKPushSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        lease = serializer.validated_data["lease"]
        if lease.tenant_id != tenant.id:
            return Response({"detail": "You can only pay your own lease."}, status=403)
        try:
            stk = request_stk_push(
                lease=lease,
                phone=serializer.validated_data.get("phone") or tenant.phone,
                amount=serializer.validated_data.get("amount"),
                actor=request.user,
                purpose=MpesaRequest.Purpose.PAY_NOW,
            )
        except Exception as exc:  # noqa: BLE001
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(
            {
                "id": str(stk.id),
                "status": stk.status,
                "message": "Check your phone and enter your M-Pesa PIN to complete payment.",
            },
            status=status.HTTP_201_CREATED,
        )
