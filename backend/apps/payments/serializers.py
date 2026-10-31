from django.utils import timezone
from rest_framework import serializers

from apps.leases.models import Lease
from apps.payments.models import MpesaRequest, Payment, Receipt
from apps.tenants.models import Tenant


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ("id", "number", "issued_at", "issued_by", "sms_sent")


class PaymentSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True, default="")
    unit_code = serializers.CharField(source="unit.code", read_only=True, default="")
    property_name = serializers.CharField(source="unit.property.name", read_only=True, default="")
    received_by_name = serializers.CharField(source="received_by.full_name", read_only=True, default="")
    receipt_number = serializers.CharField(source="receipt.number", read_only=True, default="")
    has_receipt = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "tenant",
            "tenant_name",
            "lease",
            "unit",
            "unit_code",
            "property_name",
            "method",
            "amount",
            "status",
            "paid_at",
            "reference",
            "provider_txn_id",
            "phone",
            "bill_ref",
            "received_by",
            "received_by_name",
            "matched_by",
            "matched_at",
            "notes",
            "match_note",
            "photo",
            "receipt_number",
            "has_receipt",
            "created_at",
        )
        read_only_fields = fields

    def get_has_receipt(self, obj):
        return hasattr(obj, "receipt")


class CashPaymentSerializer(serializers.Serializer):
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all())
    lease = serializers.PrimaryKeyRelatedField(
        queryset=Lease.objects.all(), required=False, allow_null=True
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    paid_at = serializers.DateTimeField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
    photo = serializers.ImageField(required=False, allow_null=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=120)

    def validate_photo(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Photo must be smaller than 5 MB.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        tenant = attrs["tenant"]
        lease = attrs.get("lease") or tenant.active_lease
        if tenant.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"tenant": "Tenant is not in your organization."})
        if lease is None:
            raise serializers.ValidationError({"lease": "Tenant has no active lease."})
        if lease.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"lease": "Lease is not in your organization."})
        if lease.tenant_id != tenant.id:
            raise serializers.ValidationError({"lease": "Lease does not belong to this tenant."})
        if lease.status != Lease.Status.ACTIVE:
            raise serializers.ValidationError({"lease": "Lease is not active."})
        if attrs.get("paid_at") and attrs["paid_at"] > timezone.now():
            raise serializers.ValidationError({"paid_at": "Payment date cannot be in the future."})
        attrs["lease"] = lease
        return attrs


class STKPushSerializer(serializers.Serializer):
    lease = serializers.PrimaryKeyRelatedField(queryset=Lease.objects.all())
    phone = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=1
    )

    def validate(self, attrs):
        request = self.context["request"]
        lease = attrs["lease"]
        if lease.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"lease": "Lease is not in your organization."})
        if request.user.is_tenant and lease.tenant.user_id != request.user.id:
            raise serializers.ValidationError({"lease": "You can only pay your own lease."})
        if lease.status != Lease.Status.ACTIVE:
            raise serializers.ValidationError({"lease": "Lease is not active."})
        return attrs


class MatchPaymentSerializer(serializers.Serializer):
    lease = serializers.PrimaryKeyRelatedField(queryset=Lease.objects.all())
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_lease(self, value):
        request = self.context["request"]
        if value.organization_id != request.user.organization_id:
            raise serializers.ValidationError("Lease is not in your organization.")
        return value


class ReversalSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class MpesaRequestSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True, default="")
    unit_code = serializers.CharField(source="lease.unit.code", read_only=True, default="")

    class Meta:
        model = MpesaRequest
        fields = (
            "id",
            "tenant",
            "tenant_name",
            "lease",
            "unit_code",
            "phone",
            "amount",
            "purpose",
            "merchant_request_id",
            "checkout_request_id",
            "status",
            "result_code",
            "result_desc",
            "mpesa_receipt",
            "payment",
            "initiated_by",
            "expires_at",
            "created_at",
        )
        read_only_fields = fields


class C2BPayloadSerializer(serializers.Serializer):
    TransactionType = serializers.CharField(required=False, allow_blank=True)
    TransID = serializers.CharField()
    TransTime = serializers.CharField(required=False, allow_blank=True)
    TransAmount = serializers.DecimalField(max_digits=12, decimal_places=2)
    BusinessShortCode = serializers.CharField(required=False, allow_blank=True)
    BillRefNumber = serializers.CharField(required=False, allow_blank=True)
    InvoiceNumber = serializers.CharField(required=False, allow_blank=True)
    OrgAccountBalance = serializers.CharField(required=False, allow_blank=True)
    ThirdPartyTransID = serializers.CharField(required=False, allow_blank=True)
    MSISDN = serializers.CharField(required=False, allow_blank=True)
    FirstName = serializers.CharField(required=False, allow_blank=True)
    MiddleName = serializers.CharField(required=False, allow_blank=True)
    LastName = serializers.CharField(required=False, allow_blank=True)
