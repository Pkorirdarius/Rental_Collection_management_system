from django.http import HttpResponse
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditLog
from apps.core.permissions import IsAdmin
from apps.reports.exports import build_excel, build_report_pdf
from apps.reports.services import (
    arrears_ageing,
    dashboard_summary,
    expected_vs_collected,
    occupancy,
    overdue_tenants,
    property_income,
    report_table,
)


class AdminReportView(APIView):
    permission_classes = [IsAdmin]

    def get_organization(self, request):
        return request.user.organization


class DashboardSummaryView(AdminReportView):
    def get(self, request):
        return Response(
            dashboard_summary(
                self.get_organization(request),
                month=request.query_params.get("month"),
                property_id=request.query_params.get("property"),
            )
        )


class OverdueListView(AdminReportView):
    def get(self, request):
        return Response(
            overdue_tenants(
                self.get_organization(request),
                status_filter=request.query_params.get("status"),
                property_id=request.query_params.get("property"),
                bucket=request.query_params.get("bucket"),
            )
        )


class ExpectedVsCollectedView(AdminReportView):
    def get(self, request):
        return Response(
            expected_vs_collected(
                self.get_organization(request),
                months=int(request.query_params.get("months", 12)),
                property_id=request.query_params.get("property"),
            )
        )


class PropertyIncomeView(AdminReportView):
    def get(self, request):
        return Response(
            property_income(
                self.get_organization(request),
                start=request.query_params.get("from"),
                end=request.query_params.get("to"),
            )
        )


class OccupancyView(AdminReportView):
    def get(self, request):
        return Response(occupancy(self.get_organization(request)))


class ArrearsAgeingView(AdminReportView):
    def get(self, request):
        return Response(arrears_ageing(self.get_organization(request)))


class ReportExportView(AdminReportView):
    def get(self, request):
        report_type = request.query_params.get("type", "")
        fmt = request.query_params.get("format", "pdf").lower()
        if fmt not in {"pdf", "xlsx"}:
            return Response({"detail": "format must be pdf or xlsx."}, status=400)
        try:
            title, headers, rows = report_table(
                self.get_organization(request), report_type, request.query_params
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        stamp = request.query_params.get("month") or request.query_params.get("from") or ""
        subtitle = f"Period: {stamp}" if stamp else ""
        if fmt == "xlsx":
            content = build_excel(title, headers, rows)
            response = HttpResponse(
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{report_type}.xlsx"'
            return response
        content = build_report_pdf(
            self.get_organization(request), title, headers, rows, subtitle=subtitle
        )
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{report_type}.pdf"'
        return response


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.full_name", read_only=True, default="")

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "action",
            "actor",
            "model_name",
            "object_id",
            "object_repr",
            "changes",
            "ip_address",
            "hash",
            "created_at",
        )
        read_only_fields = fields


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return AuditLog.objects.filter(
            organization=self.request.user.organization
        ).select_related("actor")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()[:500]
        return Response(
            [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "actor": log.actor.full_name if log.actor else "",
                    "model": log.model_name,
                    "object_id": log.object_id,
                    "object": log.object_repr,
                    "changes": log.changes,
                    "ip": log.ip_address,
                    "hash": log.hash,
                    "created_at": log.created_at,
                }
                for log in qs
            ]
        )
