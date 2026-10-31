from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.reports.views import (
    ArrearsAgeingView,
    AuditLogViewSet,
    DashboardSummaryView,
    ExpectedVsCollectedView,
    OccupancyView,
    OverdueListView,
    PropertyIncomeView,
    ReportExportView,
)

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("dashboard/summary", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/overdue", OverdueListView.as_view(), name="dashboard-overdue"),
    path(
        "reports/expected-vs-collected",
        ExpectedVsCollectedView.as_view(),
        name="report-expected",
    ),
    path("reports/property-income", PropertyIncomeView.as_view(), name="report-property-income"),
    path("reports/occupancy", OccupancyView.as_view(), name="report-occupancy"),
    path("reports/arrears-ageing", ArrearsAgeingView.as_view(), name="report-ageing"),
    path("reports/export", ReportExportView.as_view(), name="report-export"),
    path("", include(router.urls)),
]
