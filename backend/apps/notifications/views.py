from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdmin, IsAdminOrCaretaker
from apps.core.scoping import assigned_property_ids, is_admin, is_caretaker, is_tenant, scope_org
from apps.notifications.models import (
    MessageLog,
    Notification,
    PromiseToPay,
    Reminder,
    ReminderSetting,
)
from apps.notifications.serializers import (
    ManualReminderSerializer,
    MessageLogSerializer,
    NotificationSerializer,
    PromiseSerializer,
    PromiseUpdateSerializer,
    ReminderSerializer,
    ReminderSettingSerializer,
)
from apps.notifications.services import create_manual_reminder, send_reminder


def scope_lease_related(qs, user):
    if is_admin(user):
        return scope_org(qs, user)
    if is_caretaker(user):
        return scope_org(qs, user).filter(
            lease__unit__property__in=assigned_property_ids(user)
        )
    if is_tenant(user):
        return scope_org(qs, user).filter(tenant__user=user)
    return qs.none()


class ReminderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReminderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "reminder_type", "lease", "tenant"]
    search_fields = ["tenant__full_name", "tenant__phone", "lease__unit__code"]
    ordering_fields = ["scheduled_for", "created_at"]

    def get_queryset(self):
        return scope_lease_related(
            Reminder.objects.select_related("tenant", "lease", "lease__unit", "lease__unit__property"),
            self.request.user,
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        if not (request.user.is_admin or request.user.is_caretaker):
            return Response({"detail": "Not allowed."}, status=403)
        reminder = self.get_object()
        reminder = send_reminder(reminder, actor=request.user)
        return Response(ReminderSerializer(reminder).data)

    @action(detail=False, methods=["post"])
    def manual(self, request):
        if not (request.user.is_admin or request.user.is_caretaker):
            return Response({"detail": "Not allowed."}, status=403)
        serializer = ManualReminderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        reminder = create_manual_reminder(
            serializer.validated_data["lease"],
            actor=request.user,
            message=serializer.validated_data.get("message", ""),
        )
        return Response(ReminderSerializer(reminder).data, status=status.HTTP_201_CREATED)


class PromiseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrCaretaker]
    filterset_fields = ["status", "lease", "tenant"]
    ordering_fields = ["promised_date", "created_at"]

    def get_queryset(self):
        return scope_lease_related(
            PromiseToPay.objects.select_related("tenant", "lease", "lease__unit"),
            self.request.user,
        )

    def get_serializer_class(self):
        if self.action in {"update", "partial_update"}:
            return PromiseUpdateSerializer
        return PromiseSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdmin()]
        return super().get_permissions()


class ReminderSettingView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        setting = ReminderSetting.get_for_org(request.user.organization)
        return Response(ReminderSettingSerializer(setting).data)

    def patch(self, request):
        setting = ReminderSetting.get_for_org(request.user.organization)
        serializer = ReminderSettingSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MessageLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageLogSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["status", "channel", "tenant"]
    search_fields = ["phone", "body", "tenant__full_name"]
    ordering_fields = ["created_at", "sent_at"]

    def get_queryset(self):
        return MessageLog.objects.filter(
            organization=self.request.user.organization
        ).select_related("tenant")


class NotificationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["read_at"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        from django.utils import timezone

        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        from django.utils import timezone

        updated = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": updated})
