from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.properties.urls")),
    path("", include("apps.tenants.urls")),
    path("", include("apps.leases.urls")),
    path("", include("apps.ledger.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.reports.urls")),
]
