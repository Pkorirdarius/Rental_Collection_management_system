import uuid

from django.conf import settings
from django.db import models

from apps.accounts.utils import normalize_phone
from apps.core.fields import EncryptedTextField
from apps.core.models import Organization, SoftDeleteModel


class Tenant(SoftDeleteModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="tenants")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tenant_profile",
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    alt_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    national_id = EncryptedTextField(blank=True, default="")
    emergency_contact = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["organization", "phone"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self) -> str:
        return self.full_name

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        self.alt_phone = normalize_phone(self.alt_phone) or ""
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    @property
    def active_lease(self):
        return self.leases.filter(status="ACTIVE").select_related("unit__property").first()

    @property
    def portal_enabled(self) -> bool:
        return bool(self.user_id and self.user and self.user.is_active)
