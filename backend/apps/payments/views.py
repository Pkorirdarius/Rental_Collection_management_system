import logging

from django.http import FileResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdmin, IsAdminOrCaretaker
from apps.core.scoping import scope_org, scope_payment_queryset
from apps.payments.models import MpesaCallbackLog, MpesaRequest, Payment
from apps.payments.receipts import build_receipt_pdf
from apps.payments.serializers import (
    C2BPayloadSerializer,
    CashPaymentSerializer,
    MatchPaymentSerializer,
    MpesaRequestSerializer,
    PaymentSerializer,
    ReversalSerializer,
    STKPushSerializer,
)
from apps.payments.services import (
    ingest_mpesa_payment,
    match_payment,
    process_stk_callback,
    record_cash_payment,
    request_stk_push,
    reverse_payment,
)

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["method", "status", "lease", "tenant", "unit"]
    ordering_fields = ["paid_at", "amount", "created_at"]
    search_fields = ["reference", "provider_txn_id", "phone", "tenant__full_name"]

    def get_queryset(self):
        qs = Payment.objects.select_related(
            "tenant", "lease", "unit", "unit__property", "received_by", "receipt"
        )
        qs = scope_payment_queryset(qs, self.request.user)
        start = self.request.query_params.get("from")
        end = self.request.query_params.get("to")
        if start:
            qs = qs.filter(paid_at__date__gte=start)
        if end:
            qs = qs.filter(paid_at__date__lte=end)
        return qs


class CashPaymentCreateView(APIView):
    permission_classes = [IsAdminOrCaretaker]
    throttle_scope = "mpesa"

    def post(self, request):
        serializer = CashPaymentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            payment, receipt = record_cash_payment(
                organization=request.user.organization,
                tenant=data["tenant"],
                lease=data.get("lease"),
                amount=data["amount"],
                paid_at=data.get("paid_at"),
                received_by=request.user,
                note=data.get("note", ""),
                photo=data.get("photo"),
                created_by=request.user,
                idempotency_key=data.get("idempotency_key") or None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        payload = PaymentSerializer(payment, context={"request": request}).data
        payload["receipt_number"] = receipt.number if receipt else ""
        return Response(payload, status=status.HTTP_201_CREATED)


class ReversePaymentView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        payment = scope_payment_queryset(Payment.objects.all(), request.user).filter(pk=pk).first()
        if not payment:
            return Response({"detail": "Payment not found."}, status=404)
        serializer = ReversalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reversals = reverse_payment(
                payment,
                reason=serializer.validated_data.get("reason", ""),
                actor=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"payment": PaymentSerializer(payment).data, "reversals": [str(r.id) for r in reversals]}
        )


class MatchPaymentView(APIView):
    permission_classes = [IsAdminOrCaretaker]

    def post(self, request, pk):
        payment = scope_payment_queryset(Payment.objects.all(), request.user).filter(pk=pk).first()
        if not payment:
            return Response({"detail": "Payment not found."}, status=404)
        serializer = MatchPaymentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            payment = match_payment(
                payment,
                lease=serializer.validated_data["lease"],
                actor=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)


class UnmatchedPaymentListView(APIView):
    permission_classes = [IsAdminOrCaretaker]

    def get(self, request):
        qs = scope_payment_queryset(
            Payment.objects.filter(status=Payment.Status.UNMATCHED).select_related(
                "tenant", "unit", "unit__property"
            ),
            request.user,
        )
        return Response(PaymentSerializer(qs, many=True).data)


class ReceiptDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payment = scope_payment_queryset(Payment.objects.all(), request.user).filter(pk=pk).first()
        if not payment:
            return Response({"detail": "Payment not found."}, status=404)
        receipt = getattr(payment, "receipt", None)
        if receipt is None:
            return Response({"detail": "No receipt for this payment."}, status=404)
        if receipt.pdf_file:
            try:
                return FileResponse(
                    receipt.pdf_file.open("rb"),
                    as_attachment=True,
                    filename=f"{receipt.number}.pdf",
                    content_type="application/pdf",
                )
            except FileNotFoundError:
                pass
        pdf = build_receipt_pdf(payment, receipt)
        return HttpResponse(pdf, content_type="application/pdf")


class STKPushView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "mpesa"

    def post(self, request):
        if request.user.is_caretaker:
            return Response({"detail": "Caretakers cannot initiate STK push."}, status=403)
        serializer = STKPushSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            stk = request_stk_push(
                lease=data["lease"],
                phone=data.get("phone"),
                amount=data.get("amount"),
                actor=request.user,
                purpose=MpesaRequest.Purpose.PAY_NOW,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to client
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(MpesaRequestSerializer(stk).data, status=status.HTTP_201_CREATED)


class RequestPaymentView(APIView):
    permission_classes = [IsAdmin]
    throttle_scope = "mpesa"

    def post(self, request):
        serializer = STKPushSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            stk = request_stk_push(
                lease=data["lease"],
                phone=data.get("phone"),
                amount=data.get("amount"),
                actor=request.user,
                purpose=MpesaRequest.Purpose.REQUEST,
            )
        except Exception as exc:  # noqa: BLE001
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(MpesaRequestSerializer(stk).data, status=status.HTTP_201_CREATED)


class MpesaRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        qs = MpesaRequest.objects.select_related("tenant", "lease", "lease__unit")
        if request.user.is_admin:
            qs = scope_org(qs, request.user)
        elif request.user.is_tenant:
            qs = scope_org(qs, request.user).filter(tenant__user=request.user)
        else:
            qs = qs.none()
        stk = qs.filter(pk=pk).first()
        if not stk:
            return Response({"detail": "Request not found."}, status=404)
        return Response(MpesaRequestSerializer(stk).data)


class MpesaWebhookMixin:
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "mpesa"

    def check_access(self, request, token_setting="CALLBACK_TOKEN"):
        from django.conf import settings

        expected = settings.MPESA.get(token_setting, "")
        provided = request.query_params.get("token", "")
        if expected and provided != expected:
            return False
        if not expected and not settings.DEBUG:
            return False
        allowlist = settings.MPESA.get("IP_ALLOWLIST") or []
        if allowlist:
            remote = (
                request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or request.META.get("REMOTE_ADDR", "")
            )
            if remote not in allowlist:
                return False
        return True

    def log_callback(self, request, endpoint, payload, error=""):
        headers = {
            key: value
            for key, value in request.META.items()
            if key.startswith("HTTP_") and key not in {"HTTP_AUTHORIZATION", "HTTP_COOKIE"}
        }
        return MpesaCallbackLog.objects.create(
            endpoint=endpoint,
            http_method=request.method,
            ip_address=request.META.get("REMOTE_ADDR"),
            headers=headers,
            payload=payload,
            processed=not bool(error),
            error=error,
        )


class C2BValidationView(MpesaWebhookMixin, APIView):
    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        if not self.check_access(request, "VALIDATION_TOKEN"):
            return Response({"ResultCode": 1, "ResultDesc": "Rejected"}, status=403)
        log = self.log_callback(request, "c2b-validation", payload)
        serializer = C2BPayloadSerializer(data=payload)
        if not serializer.is_valid():
            log.processed = False
            log.error = str(serializer.errors)
            log.save(update_fields=["processed", "error"])
            return Response({"ResultCode": 1, "ResultDesc": "Invalid payload"})
        if serializer.validated_data["TransAmount"] <= 0:
            return Response({"ResultCode": 1, "ResultDesc": "Invalid amount"})
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class C2BConfirmationView(MpesaWebhookMixin, APIView):
    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        if not self.check_access(request, "CALLBACK_TOKEN"):
            return Response({"ResultCode": 1, "ResultDesc": "Rejected"}, status=403)
        log = self.log_callback(request, "c2b-confirmation", payload)
        serializer = C2BPayloadSerializer(data=payload)
        if not serializer.is_valid():
            log.processed = False
            log.error = str(serializer.errors)
            log.save(update_fields=["processed", "error"])
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
        data = serializer.validated_data
        try:
            payment, _ = ingest_mpesa_payment(
                receipt=data["TransID"],
                amount=data["TransAmount"],
                phone=data.get("MSISDN", ""),
                bill_ref=data.get("BillRefNumber", ""),
                shortcode=data.get("BusinessShortCode", ""),
                paid_at=None,
                raw_payload=payload,
            )
            if payment:
                log.organization = payment.organization
                log.save(update_fields=["organization"])
        except Exception as exc:  # noqa: BLE001 - never fail the callback
            logger.exception("C2B confirmation processing failed")
            log.processed = False
            log.error = str(exc)[:1000]
            log.save(update_fields=["processed", "error"])
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class C2BResultView(MpesaWebhookMixin, APIView):
    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        if not self.check_access(request, "CALLBACK_TOKEN"):
            return Response({"ResultCode": 1, "ResultDesc": "Rejected"}, status=403)
        self.log_callback(request, "c2b-result", payload)
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class STKCallbackView(MpesaWebhookMixin, APIView):
    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        if not self.check_access(request, "CALLBACK_TOKEN"):
            return Response({"ResultCode": 1, "ResultDesc": "Rejected"}, status=403)
        log = self.log_callback(request, "stk-callback", payload)
        try:
            stk = process_stk_callback(payload)
            if stk:
                log.organization = stk.organization
                log.save(update_fields=["organization"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("STK callback processing failed")
            log.processed = False
            log.error = str(exc)[:1000]
            log.save(update_fields=["processed", "error"])
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
