import uuid

from django.conf import settings
from django.db import models

from apps.core.models import Organization


class LedgerEntry(models.Model):
    """Append-only double-entry-style record. Debits are positive, credits negative."""

    class Type(models.TextChoices):
        RENT_CHARGE = "RENT_CHARGE", "Rent charge"
        LATE_FEE = "LATE_FEE", "Late fee"
        PAYMENT = "PAYMENT", "Payment"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        WAIVER = "WAIVER", "Waiver"
        DEPOSIT = "DEPOSIT", "Deposit received"
        DEPOSIT_REFUND = "DEPOSIT_REFUND", "Deposit refund"
        REVERSAL = "REVERSAL", "Reversal"

    class Source(models.TextChoices):
        SYSTEM = "SYSTEM", "System"
        CASH = "CASH", "Cash"
        MPESA = "MPESA", "M-Pesa"
        MANUAL = "MANUAL", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    lease = models.ForeignKey("leases.Lease", on_delete=models.PROTECT, related_name="ledger_entries")
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.PROTECT, related_name="ledger_entries"
    )
    unit = models.ForeignKey("properties.Unit", on_delete=models.PROTECT, related_name="ledger_entries")
    entry_type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Signed amount: debit positive, credit negative."
    )
    effective_date = models.DateField(db_index=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.SYSTEM)
    payment = models.ForeignKey(
        "payments.Payment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    reversal_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversals"
    )
    idempotency_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ledger_entries_created",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["effective_date", "created_at"]
        indexes = [
            models.Index(fields=["lease", "effective_date"]),
            models.Index(fields=["organization", "entry_type", "effective_date"]),
            models.Index(fields=["tenant", "effective_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.entry_type} {self.amount} ({self.lease_id})"

    def save(self, *args, **kwargs):
        if self.pk and LedgerEntry.objects.filter(pk=self.pk).exists():
            raise ValueError("Ledger entries are immutable; post a reversal instead")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Ledger entries cannot be deleted; post a reversal instead")
