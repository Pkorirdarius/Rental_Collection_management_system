from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.ledger.views import (
    AdjustmentCreateView,
    LedgerEntryViewSet,
    LedgerSummaryView,
    ReversalCreateView,
)

router = DefaultRouter()
router.register("ledger", LedgerEntryViewSet, basename="ledger")

urlpatterns = [
    path("", include(router.urls)),
    path("ledger/adjustments", AdjustmentCreateView.as_view(), name="ledger-adjustment"),
    path("ledger/<uuid:pk>/reverse", ReversalCreateView.as_view(), name="ledger-reverse"),
    path("ledger-summary", LedgerSummaryView.as_view(), name="ledger-summary"),
]
