from rest_framework import serializers

from apps.leases.models import Lease
from apps.notifications.models import (
    MessageLog,
    Notification,
    PromiseToPay,
    Reminder,
    ReminderSetting,
)


class ReminderSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    unit_code = serializers.CharField(source="lease.unit.code", read_only=True)
    property_name = serializers.CharField(source="lease.unit.property.name", read_only=True)

    class Meta:
        model = Reminder
        fields = (
            "id",
            "lease",
            "tenant",
            "tenant_name",
            "unit_code",
            "property_name",
            "reminder_type",
            "period_key",
            "scheduled_for",
            "sent_at",
            "status",
            "amount_due",
            "days_overdue",
            "message",
            "error",
            "created_at",
        )
        read_only_fields = fields


class ManualReminderSerializer(serializers.Serializer):
    lease = serializers.PrimaryKeyRelatedField(queryset=Lease.objects.all())
    message = serializers.CharField(required=False, allow_blank=True, max_length=480)

    def validate_lease(self, value):
        request = self.context["request"]
        if value.organization_id != request.user.organization_id:
            raise serializers.ValidationError("Lease is not in your organization.")
        return value


class PromiseSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    unit_code = serializers.CharField(source="lease.unit.code", read_only=True)

    class Meta:
        model = PromiseToPay
        fields = (
            "id",
            "lease",
            "tenant",
            "tenant_name",
            "unit_code",
            "amount",
            "promised_date",
            "note",
            "status",
            "created_by",
            "resolved_at",
            "resolution_note",
            "created_at",
        )
        read_only_fields = ("id", "tenant", "created_by", "resolved_at", "created_at")

    def validate_lease(self, value):
        request = self.context["request"]
        if value.organization_id != request.user.organization_id:
            raise serializers.ValidationError("Lease is not in your organization.")
        return value

    def create(self, validated_data):
        lease = validated_data["lease"]
        validated_data["organization"] = lease.organization
        validated_data["tenant"] = lease.tenant
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class PromiseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromiseToPay
        fields = ("status", "resolution_note", "promised_date", "amount")

    def update(self, instance, validated_data):
        from django.utils import timezone

        instance = super().update(instance, validated_data)
        resolved_statuses = {
            PromiseToPay.Status.KEPT,
            PromiseToPay.Status.BROKEN,
            PromiseToPay.Status.CANCELLED,
        }
        if instance.status in resolved_statuses:
            instance.resolved_at = timezone.now()
            instance.save(update_fields=["resolved_at", "updated_at"])
        return instance


class ReminderSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderSetting
        fields = (
            "enabled",
            "pre_due_days",
            "escalation_offsets",
            "send_hour",
            "language",
            "sender_id",
            "updated_at",
        )
        read_only_fields = ("updated_at",)

    def validate_escalation_offsets(self, value):
        if not isinstance(value, list) or any(not isinstance(v, int) or v <= 0 for v in value):
            raise serializers.ValidationError("Provide a list of positive day offsets.")
        return sorted(set(value))

    def validate_send_hour(self, value):
        if value > 23:
            raise serializers.ValidationError("Send hour must be between 0 and 23.")
        return value

    def validate_language(self, value):
        if value not in {"en", "sw"}:
            raise serializers.ValidationError("Language must be en or sw.")
        return value


class MessageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageLog
        fields = (
            "id",
            "tenant",
            "phone",
            "channel",
            "template",
            "body",
            "status",
            "provider_message_id",
            "cost",
            "error",
            "retry_count",
            "sent_at",
            "created_at",
        )
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "body", "level", "link", "read_at", "created_at")
        read_only_fields = fields
