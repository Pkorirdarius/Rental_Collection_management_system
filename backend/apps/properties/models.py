import builtins
import re
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import Organization, SoftDeleteModel, TimeStampedModel


def normalize_code(value: str) -> str:
    return re.sub(r"[^A-Z0-9-]", "", (value or "").upper())[:20]


class Property(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="properties")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    county = models.CharField(max_length=80, blank=True)
    mpesa_shortcode_override = models.CharField(max_length=12, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="unique_property_code_per_org")
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code)
        super().save(*args, **kwargs)

    @property
    def mpesa_shortcode(self) -> str:
        return self.mpesa_shortcode_override or self.organization.mpesa_shortcode


class Unit(SoftDeleteModel):
    class Status(models.TextChoices):
        VACANT = "VACANT", "Vacant"
        OCCUPIED = "OCCUPIED", "Occupied"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="units")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    code = models.CharField(max_length=20)
    mpesa_bill_ref = models.CharField(max_length=30, blank=True)
    unit_type = models.CharField(max_length=60, blank=True)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    default_rent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    default_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.VACANT)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["property__name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["property", "code"], name="unique_unit_code_per_property"),
            models.UniqueConstraint(
                fields=["organization", "mpesa_bill_ref"],
                condition=~Q(mpesa_bill_ref=""),
                name="unique_mpesa_bill_ref_per_org",
            ),
        ]
        indexes = [models.Index(fields=["organization", "mpesa_bill_ref"])]

    def __str__(self) -> str:
        return f"{self.property.code}-{self.code}"

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code)
        self.organization = self.property.organization
        if not self.mpesa_bill_ref:
            self.mpesa_bill_ref = f"{self.property.code}-{self.code}"
        self.mpesa_bill_ref = normalize_code(self.mpesa_bill_ref)
        super().save(*args, **kwargs)

    @builtins.property
    def active_lease(self):
        return self.leases.filter(status="ACTIVE").select_related("tenant").first()


class PropertyAssignment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="property_assignments"
    )
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="assignments")

    class Meta:
        ordering = ["property__name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "property"], name="unique_caretaker_property")
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.property}"
