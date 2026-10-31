from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.audit import audit
from apps.core.models import AuditLog
from apps.core.permissions import IsAdmin, IsAdminOrCaretakerReadOnly
from apps.core.scoping import assigned_property_ids, is_admin, scope_org
from apps.core.viewsets import AuditedModelViewSet
from apps.properties.models import Property, PropertyAssignment, Unit
from apps.properties.serializers import (
    PropertyAssignmentSerializer,
    PropertySerializer,
    UnitSerializer,
)


class PropertyViewSet(AuditedModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAdminOrCaretakerReadOnly]
    search_fields = ["name", "code", "address", "county"]
    ordering_fields = ["name", "created_at"]
    filterset_fields = ["is_active", "county"]

    def get_queryset(self):
        qs = Property.objects.select_related("organization").annotate(
            _units=Count("units", distinct=True)
        )
        user = self.request.user
        if is_admin(user):
            return scope_org(qs, user)
        return scope_org(qs, user).filter(id__in=assigned_property_ids(user))

    def get_permissions(self):
        if self.action in {"assign_caretaker", "remove_caretaker", "assignments"}:
            return [IsAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["get"], url_path="assignments")
    def assignments(self, request, pk=None):
        property_obj = self.get_object()
        data = PropertyAssignmentSerializer(
            property_obj.assignments.select_related("user"), many=True
        ).data
        return Response(data)

    @action(detail=True, methods=["post"], url_path="assign-caretaker")
    def assign_caretaker(self, request, pk=None):
        property_obj = self.get_object()
        serializer = PropertyAssignmentSerializer(
            data={"user": request.data.get("user"), "property": property_obj.id},
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        audit(AuditLog.Action.CREATE, obj=assignment, organization=property_obj.organization)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="remove-caretaker")
    def remove_caretaker(self, request, pk=None):
        property_obj = self.get_object()
        user_id = request.data.get("user")
        deleted, _ = PropertyAssignment.objects.filter(
            property=property_obj, user_id=user_id
        ).delete()
        audit(
            AuditLog.Action.DELETE,
            obj=property_obj,
            changes={"removed_caretaker": str(user_id)},
        )
        return Response({"deleted": deleted})


class UnitViewSet(AuditedModelViewSet):
    serializer_class = UnitSerializer
    permission_classes = [IsAdminOrCaretakerReadOnly]
    search_fields = ["code", "mpesa_bill_ref", "unit_type", "property__name"]
    ordering_fields = ["code", "created_at", "default_rent"]
    filterset_fields = ["status", "property", "unit_type"]

    def get_queryset(self):
        qs = Unit.objects.select_related("property", "organization")
        user = self.request.user
        if is_admin(user):
            qs = scope_org(qs, user)
        else:
            qs = scope_org(qs, user).filter(property_id__in=assigned_property_ids(user))
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs

    def perform_create(self, serializer):
        unit = serializer.save(organization=self.request.user.organization)
        audit(AuditLog.Action.CREATE, obj=unit)


class CaretakerListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = PropertyAssignmentSerializer
    queryset = PropertyAssignment.objects.select_related("user", "property")

    def get_queryset(self):
        return self.queryset.filter(user__organization=self.request.user.organization)


class AssignmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = PropertyAssignmentSerializer
    queryset = PropertyAssignment.objects.select_related("user", "property")
    filterset_fields = ["property", "user"]

    def get_queryset(self):
        return self.queryset.filter(user__organization=self.request.user.organization)

    def perform_create(self, serializer):
        assignment = serializer.save()
        audit(AuditLog.Action.CREATE, obj=assignment)
