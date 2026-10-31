from rest_framework import serializers

from apps.leases.models import Lease
from apps.properties.models import Unit


class LeaseSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    tenant_phone = serializers.CharField(source="tenant.phone", read_only=True)
    unit_code = serializers.CharField(source="unit.code", read_only=True)
    property_name = serializers.CharField(source="unit.property.name", read_only=True)
    property_id = serializers.UUIDField(source="unit.property_id", read_only=True)
    balance = serializers.SerializerMethodField()
    days_overdue = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Lease
        fields = (
            "id",
            "tenant",
            "tenant_name",
            "tenant_phone",
            "unit",
            "unit_code",
            "property_name",
            "property_id",
            "start_date",
            "end_date",
            "rent_amount",
            "due_day",
            "grace_period_days",
            "deposit_amount",
            "deposit_paid",
            "late_fee_type",
            "late_fee_value",
            "late_fee_applies_after_grace",
            "proration_enabled",
            "status",
            "terminated_at",
            "termination_reason",
            "notes",
            "balance",
            "days_overdue",
            "payment_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "terminated_at", "created_at", "updated_at")

    def get_balance(self, obj):
        from apps.ledger.services import lease_balance

        return str(lease_balance(obj))

    def get_days_overdue(self, obj):
        from apps.ledger.services import days_overdue

        return days_overdue(obj)

    def get_payment_status(self, obj):
        from apps.ledger.services import lease_status

        return lease_status(obj)

    def validate(self, attrs):
        request = self.context["request"]
        unit = attrs.get("unit") or getattr(self.instance, "unit", None)
        tenant = attrs.get("tenant") or getattr(self.instance, "tenant", None)
        start_date = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        status = attrs.get("status", getattr(self.instance, "status", Lease.Status.ACTIVE))

        if unit and unit.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"unit": "Unit does not belong to your organization."})
        if tenant and tenant.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"tenant": "Tenant does not belong to your organization."})
        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})

        if status == Lease.Status.ACTIVE and unit:
            qs = Lease.objects.filter(unit=unit, status=Lease.Status.ACTIVE)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"unit": "Unit already has an active lease."})
        return attrs

    def create(self, validated_data):
        validated_data["organization"] = self.context["request"].user.organization
        validated_data["created_by"] = self.context["request"].user
        lease = super().create(validated_data)
        Unit.objects.filter(pk=lease.unit_id).update(status=Unit.Status.OCCUPIED)
        return lease

    def update(self, instance, validated_data):
        lease = super().update(instance, validated_data)
        if lease.status == Lease.Status.ACTIVE:
            Unit.objects.filter(pk=lease.unit_id).update(status=Unit.Status.OCCUPIED)
        elif lease.status in {Lease.Status.ENDED, Lease.Status.TERMINATED}:
            if not Lease.objects.filter(unit=lease.unit, status=Lease.Status.ACTIVE).exists():
                Unit.objects.filter(pk=lease.unit_id).update(status=Unit.Status.VACANT)
        return lease


class LeaseTerminateSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    ended_on = serializers.DateField(required=False)

    def save(self, lease):
        if self.validated_data.get("ended_on"):
            lease.end_date = self.validated_data["ended_on"]
        lease.terminate(reason=self.validated_data.get("reason", ""))
        return lease
