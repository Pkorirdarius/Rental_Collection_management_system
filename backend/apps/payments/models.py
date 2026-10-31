import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Organization, TimeStampedModel


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        MPESA_C2B = "MPESA_C2B", "M-Pesa C2B"
        MPESA_STK = "MPESA_STK", "M-Pesa STK Push"
        BANK = "BANK", "Bank transfer"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        UNMATCHED = "UNMATCHED", "Unmatched"
        FAILED = "FAILED", "Failed"
        REVERSED = "REVERSED", "Reversed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="payments")
    tenant = models.ForeignKey(
        "tenants.Tenant", null=True, blank=True, on_delete=models.PROTECT, related_name="payments"
    )
    lease = models.ForeignKey(
        "leases.Lease", null=True, blank=True, on_delete=models.PROTECT, related_name="payments"
    )
    unit = models.ForeignKey(
        "properties.Unit", null=True, blank=True, on_delete=models.PROTECT, related_name="payments"
    )
    method = models.CharField(max_length=15, choices=Method.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(default=timezone.now, db_index=True)
    reference = models.CharField(
        max_length=60, blank=True, help_text="M-Pesa receipt number or internal cash receipt number."
    )
    provider_txn_id = models.CharField(max_length=60, blank=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    bill_ref = models.CharField(max_length=30, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments_received",
    )
    matched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments_matched",
    )
    matched_at = models.DateTimeField(null=True, blank=True)
    photo = models.ImageField(upload_to="cash_photos/%Y/%m/", null=True, blank=True)
    notes = models.TextField(blank=True)
    reversal_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversals"
    )
    idempotency_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    match_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-paid_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "reference"],
                condition=~Q(reference=""),
                name="unique_payment_reference_per_org",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status", "paid_at"]),
            models.Index(fields=["organization", "method", "paid_at"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference or self.id} {self.amount} {self.method}"

    @property
    def is_mpesa(self) -> bool:
        return self.method in {self.Method.MPESA_C2B, self.Method.MPESA_STK}

    @property
    def receipt_number(self) -> str:
        receipt = getattr(self, "receipt", None)
        return receipt.number if receipt else ""


class MpesaRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        TIMEOUT = "TIMEOUT", "Timeout"

    class Purpose(models.TextChoices):
        PAY_NOW = "PAY_NOW", "Tenant pay now"
        REQUEST = "REQUEST", "Landlord request payment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="mpesa_requests"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant", null=True, blank=True, on_delete=models.PROTECT, related_name="mpesa_requests"
    )
    lease = models.ForeignKey(
        "leases.Lease", null=True, blank=True, on_delete=models.PROTECT, related_name="mpesa_requests"
    )
    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.CharField(max_length=10, choices=Purpose.choices, default=Purpose.PAY_NOW)
    merchant_request_id = models.CharField(max_length=80, blank=True)
    checkout_request_id = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    result_code = models.CharField(max_length=10, blank=True)
    result_desc = models.CharField(max_length=255, blank=True)
    mpesa_receipt = models.CharField(max_length=60, blank=True)
    payment = models.OneToOneField(
        Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="stk_request"
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mpesa_requests_initiated",
    )
    raw_response = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "status", "created_at"])]

    def __str__(self) -> str:
        return f"STK {self.checkout_request_id} {self.status}"


class MpesaCallbackLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name="callback_logs"
    )
    endpoint = models.CharField(max_length=80)
    http_method = models.CharField(max_length=10, default="POST")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    processed = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["endpoint", "created_at"])]

    def __str__(self) -> str:
        return f"{self.endpoint} {self.created_at}"


class ReceiptSequence(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="receipt_sequences"
    )
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "year"], name="unique_receipt_sequence")
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}-{self.year}:{self.last_number}"


class Receipt(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="receipts")
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="receipt")
    number = models.CharField(max_length=40, unique=True)
    issued_at = models.DateTimeField(default=timezone.now)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="receipts_issued",
    )
    pdf_file = models.FileField(upload_to="receipts/%Y/%m/", blank=True)
    sms_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return self.number


class ReconciliationRun(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name="reconciliations"
    )
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    checked = models.PositiveIntegerField(default=0)
    matched = models.PositiveIntegerField(default=0)
    unmatched = models.PositiveIntegerField(default=0)
    errors = models.PositiveIntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]


class PaymentEvent(models.Model):
    """Append-only timeline for a payment (recorded, matched, reversed, SMS...)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="events")
    event = models.CharField(max_length=40)
    detail = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.event} {self.payment_id}"
