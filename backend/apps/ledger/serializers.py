from decimal import Decimal

from rest_framework import serializers

from apps.ledger.models import LedgerEntry


class LedgerEntrySerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.full_name", read_only=True)
    unit_code = serializers.CharField(source="unit.code", read_only=True)
    property_name = serializers.CharField(source="unit.property.name", read_only=True)
    payment_reference = serializers.CharField(source="payment.reference", read_only=True, default="")

    class Meta:
        model = LedgerEntry
        fields = (
            "id",
            "lease",
            "tenant",
            "tenant_name",
            "unit",
            "unit_code",
            "property_name",
            "entry_type",
            "amount",
            "effective_date",
            "period_start",
            "period_end",
            "description",
            "source",
            "payment",
            "payment_reference",
            "reversal_of",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class AdjustmentSerializer(serializers.Serializer):
    lease = serializers.PrimaryKeyRelatedField(queryset=None)
    entry_type = serializers.ChoiceField(
        choices=[LedgerEntry.Type.ADJUSTMENT, LedgerEntry.Type.WAIVER]
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    effective_date = serializers.DateField(required=False)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.leases.models import Lease

        self.fields["lease"].queryset = Lease.objects.all()

    def validate(self, attrs):
        request = self.context["request"]
        lease = attrs["lease"]
        if lease.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"lease": "Lease is not in your organization."})
        amount = attrs["amount"]
        if amount == Decimal("0.00"):
            raise serializers.ValidationError({"amount": "Amount cannot be zero."})
        if attrs["entry_type"] == LedgerEntry.Type.WAIVER and amount > 0:
            raise serializers.ValidationError({"amount": "A waiver must be a credit (negative amount)."})
        return attrs


class ReversalSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
