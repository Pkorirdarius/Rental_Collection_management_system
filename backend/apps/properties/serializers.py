from rest_framework import serializers

from apps.accounts.models import User
from apps.properties.models import Property, PropertyAssignment, Unit


class UnitSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_code = serializers.CharField(source="property.code", read_only=True)
    active_tenant = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = (
            "id",
            "property",
            "property_name",
            "property_code",
            "code",
            "mpesa_bill_ref",
            "unit_type",
            "bedrooms",
            "default_rent",
            "default_deposit",
            "status",
            "notes",
            "active_tenant",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "mpesa_bill_ref", "created_at", "updated_at")

    def get_active_tenant(self, obj) -> dict | None:
        lease = obj.active_lease
        if not lease:
            return None
        return {"id": str(lease.tenant_id), "name": lease.tenant.full_name, "lease_id": str(lease.id)}

    def validate(self, attrs):
        request = self.context["request"]
        property_obj = attrs.get("property") or getattr(self.instance, "property", None)
        if property_obj and property_obj.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"property": "Property does not belong to your organization."})
        return attrs


class PropertySerializer(serializers.ModelSerializer):
    units_count = serializers.SerializerMethodField()
    occupied_units = serializers.SerializerMethodField()
    caretakers = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id",
            "name",
            "code",
            "address",
            "city",
            "county",
            "mpesa_shortcode_override",
            "notes",
            "is_active",
            "units_count",
            "occupied_units",
            "caretakers",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "units_count", "occupied_units", "caretakers")

    def get_units_count(self, obj) -> int:
        return obj.units.count()

    def get_occupied_units(self, obj) -> int:
        return obj.units.filter(status=Unit.Status.OCCUPIED).count()

    def get_caretakers(self, obj) -> list[dict]:
        return [
            {"id": str(a.user_id), "name": a.user.full_name, "phone": a.user.phone}
            for a in obj.assignments.select_related("user")
        ]

    def create(self, validated_data):
        validated_data["organization"] = self.context["request"].user.organization
        return super().create(validated_data)


class PropertyAssignmentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = PropertyAssignment
        fields = ("id", "user", "user_name", "property", "property_name", "created_at")
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        request = self.context["request"]
        user = attrs.get("user") or getattr(self.instance, "user", None)
        property_obj = attrs.get("property") or getattr(self.instance, "property", None)
        if user.role != User.Role.CARETAKER:
            raise serializers.ValidationError({"user": "Only caretakers can be assigned to properties."})
        if user.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"user": "User is not in your organization."})
        if property_obj.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"property": "Property is not in your organization."})
        return attrs
