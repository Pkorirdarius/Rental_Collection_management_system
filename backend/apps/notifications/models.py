import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import Organization, TimeStampedModel


class ReminderSetting(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="reminder_setting"
    )
    enabled = models.BooleanField(default=True)
    pre_due_days = models.PositiveSmallIntegerField(default=3)
    escalation_offsets = models.JSONField(default=list, blank=True)
    send_hour = models.PositiveSmallIntegerField(default=8)
    language = models.CharField(max_length=5, default="en")
    sender_id = models.CharField(max_length=20, blank=True)

    def __str__(self) -> str:
        return f"Reminder settings for {self.organization}"

    def save(self, *args, **kwargs):
        if not self.escalation_offsets:
            self.escalation_offsets = [1, 3, 7, 14, 30]
        super().save(*args, **kwargs)

    @classmethod
    def get_for_org(cls, organization):
        setting, _ = cls.objects.get_or_create(
            organization=organization,
            defaults={"escalation_offsets": [1, 3, 7, 14, 30]},
        )
        return setting


class Reminder(TimeStampedModel):
    class Type(models.TextChoices):
        PRE_DUE = "PRE_DUE", "Before due date"
        DUE = "DUE", "Due today"
        OVERDUE_1 = "OVERDUE_1", "Overdue 1 day"
        OVERDUE_3 = "OVERDUE_3", "Overdue 3 days"
        OVERDUE_7 = "OVERDUE_7", "Overdue 7 days"
        OVERDUE_14 = "OVERDUE_14", "Overdue 14 days"
        OVERDUE_30 = "OVERDUE_30", "Overdue 30 days"
        MANUAL = "MANUAL", "Manual reminder"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="reminders"
    )
    lease = models.ForeignKey("leases.Lease", on_delete=models.CASCADE, related_name="reminders")
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="reminders"
    )
    reminder_type = models.CharField(max_length=20, choices=Type.choices)
    period_key = models.CharField(max_length=30)
    scheduled_for = models.DateField(default=timezone.localdate, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    days_overdue = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)
    error = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reminders_created",
    )

    class Meta:
        ordering = ["-scheduled_for", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["lease", "reminder_type", "period_key"],
                name="unique_reminder_per_lease_type_period",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status", "scheduled_for"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.reminder_type} {self.tenant} {self.period_key}"


class PromiseToPay(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        KEPT = "KEPT", "Kept"
        BROKEN = "BROKEN", "Broken"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="promises"
    )
    lease = models.ForeignKey("leases.Lease", on_delete=models.CASCADE, related_name="promises")
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="promises"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    promised_date = models.DateField()
    note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="promises_created",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["promised_date"]
        indexes = [models.Index(fields=["organization", "status", "promised_date"])]

    def __str__(self) -> str:
        return f"{self.tenant} promises {self.amount} on {self.promised_date}"


class MessageLog(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="message_logs"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant", null=True, blank=True, on_delete=models.SET_NULL, related_name="messages"
    )
    phone = models.CharField(max_length=20)
    channel = models.CharField(max_length=10, default="SMS")
    template = models.CharField(max_length=40, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    provider_message_id = models.CharField(max_length=80, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal("0.0000"))
    error = models.CharField(max_length=500, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    reminder = models.ForeignKey(
        Reminder, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages"
    )
    payment = models.ForeignKey(
        "payments.Payment", null=True, blank=True, on_delete=models.SET_NULL, related_name="messages"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "created_at"]),
            models.Index(fields=["phone", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.channel} to {self.phone} ({self.status})"


class Notification(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="notifications"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=150)
    body = models.TextField(blank=True)
    level = models.CharField(max_length=10, default="info")
    link = models.CharField(max_length=255, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self) -> str:
        return self.title
