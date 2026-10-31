from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tenants.portal_views import (
    PortalBalanceView,
    PortalPaymentsView,
    PortalPayView,
    PortalProfileView,
    PortalReceiptsView,
    PortalStatementView,
)
from apps.tenants.views import TenantViewSet

router = DefaultRouter()
router.register("tenants", TenantViewSet, basename="tenant")

portal_urlpatterns = [
    path("me", PortalProfileView.as_view(), name="portal-me"),
    path("me/balance", PortalBalanceView.as_view(), name="portal-balance"),
    path("me/payments", PortalPaymentsView.as_view(), name="portal-payments"),
    path("me/receipts", PortalReceiptsView.as_view(), name="portal-receipts"),
    path("me/statement", PortalStatementView.as_view(), name="portal-statement"),
    path("me/pay", PortalPayView.as_view(), name="portal-pay"),
]

urlpatterns = [
    path("portal/", include(portal_urlpatterns)),
    path("", include(router.urls)),
]
