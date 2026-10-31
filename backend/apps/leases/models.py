import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Organization, SoftDeleteModel


class Lease(SoftDeleteModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"
        TERMINATED = "TERMINATED", "Terminated"

    class LateFeeType(models.TextChoices):
        NONE = "NONE", "None"
        FLAT = "FLAT", "Flat amount"
        PERCENT = "PERCENT", "Percentage of rent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="leases")
    unit = models.ForeignKey("properties.Unit", on_delete=models.PROTECT, related_name="leases")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="leases")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_day = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(28)]
    )
    grace_period_days = models.PositiveSmallIntegerField(default=0)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    deposit_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    late_fee_type = models.CharField(max_length=10, choices=LateFeeType.choices, default=LateFeeType.NONE)
    late_fee_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    late_fee_applies_after_grace = models.BooleanField(default=True)
    proration_enabled = models.BooleanField(
        default=False, help_text="Prorate the first and last month by days occupied."
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    terminated_at = models.DateTimeField(null=True, blank=True)
    termination_reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leases_created",
    )

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["unit"],
                condition=Q(status="ACTIVE"),
                name="one_active_lease_per_unit",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["unit", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.tenant.full_name} - {self.unit}"

    def save(self, *args, **kwargs):
        self.organization = self.unit.organization
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        if self.unit.organization_id != self.tenant.organization_id:
            raise ValidationError("Unit and tenant must belong to the same organization.")

    @property
    def property(self):
        return self.unit.property

    def is_active_on(self, day) -> bool:
        if self.status not in {self.Status.ACTIVE, self.Status.ENDED}:
            return False
        if day < self.start_date:
            return False
        if self.end_date and day > self.end_date:
            return False
        return True

    def due_date_for(self, period_start):
        import calendar

        last_day = calendar.monthrange(period_start.year, period_start.month)[1]
        return period_start.replace(day=min(self.due_day, last_day))

    def terminate(self, *, reason="", when=None):
        self.status = self.Status.TERMINATED
        self.terminated_at = when or timezone.now()
        self.termination_reason = reason[:255]
        self.save(update_fields=["status", "terminated_at", "termination_reason", "updated_at"])
