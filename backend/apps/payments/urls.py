from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.payments.views import (
    C2BConfirmationView,
    C2BResultView,
    C2BValidationView,
    CashPaymentCreateView,
    MatchPaymentView,
    MpesaRequestDetailView,
    PaymentViewSet,
    ReceiptDownloadView,
    RequestPaymentView,
    ReversePaymentView,
    STKCallbackView,
    STKPushView,
    UnmatchedPaymentListView,
)

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("payments/cash", CashPaymentCreateView.as_view(), name="payment-cash"),
    path("payments/unmatched", UnmatchedPaymentListView.as_view(), name="payment-unmatched"),
    path("payments/mpesa/stk-push", STKPushView.as_view(), name="payment-stk-push"),
    path("payments/mpesa/request", RequestPaymentView.as_view(), name="payment-stk-request"),
    path(
        "payments/mpesa/requests/<uuid:pk>",
        MpesaRequestDetailView.as_view(),
        name="payment-stk-detail",
    ),
    path("payments/<uuid:pk>/reverse", ReversePaymentView.as_view(), name="payment-reverse"),
    path("payments/<uuid:pk>/match", MatchPaymentView.as_view(), name="payment-match"),
    path(
        "payments/<uuid:pk>/receipt.pdf",
        ReceiptDownloadView.as_view(),
        name="payment-receipt",
    ),
    path(
        "webhooks/mpesa/c2b/validation",
        C2BValidationView.as_view(),
        name="mpesa-c2b-validation",
    ),
    path(
        "webhooks/mpesa/c2b/confirmation",
        C2BConfirmationView.as_view(),
        name="mpesa-c2b-confirmation",
    ),
    path("webhooks/mpesa/c2b/result", C2BResultView.as_view(), name="mpesa-c2b-result"),
    path(
        "webhooks/mpesa/stk/callback",
        STKCallbackView.as_view(),
        name="mpesa-stk-callback",
    ),
    path("", include(router.urls)),
]
