from rest_framework import serializers

from apps.tenants.models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    portal_enabled = serializers.BooleanField(read_only=True)
    active_lease_id = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = (
            "id",
            "full_name",
            "phone",
            "alt_phone",
            "email",
            "national_id",
            "emergency_contact",
            "notes",
            "status",
            "portal_enabled",
            "active_lease_id",
            "unit",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "portal_enabled", "active_lease_id", "unit")

    def get_active_lease_id(self, obj):
        lease = obj.active_lease
        return str(lease.id) if lease else None

    def get_unit(self, obj):
        lease = obj.active_lease
        if not lease:
            return None
        return {
            "id": str(lease.unit_id),
            "code": lease.unit.code,
            "property": lease.unit.property.name,
            "bill_ref": lease.unit.mpesa_bill_ref,
        }

    def validate_phone(self, value):
        from apps.accounts.utils import normalize_phone

        phone = normalize_phone(value)
        if not phone:
            raise serializers.ValidationError("Enter a valid Kenyan phone number.")
        return phone

    def validate(self, attrs):
        request = self.context["request"]
        phone = attrs.get("phone") or getattr(self.instance, "phone", None)
        qs = Tenant.objects.filter(organization=request.user.organization, phone=phone)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({"phone": "A tenant with this phone already exists."})
        return attrs

    def create(self, validated_data):
        validated_data["organization"] = self.context["request"].user.organization
        return super().create(validated_data)


class TenantPortalInviteSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)

    def validate(self, attrs):
        tenant = self.context["tenant"]
        if not (attrs.get("email") or tenant.email):
            raise serializers.ValidationError(
                {"email": "An email address is required to create a tenant portal account."}
            )
        if tenant.user_id:
            raise serializers.ValidationError({"detail": "Tenant already has a portal account."})
        return attrs
