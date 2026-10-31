import hashlib
import json
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(TimeStampedModel):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def delete(self, using=None, keep_parents=False, *, deleted_by=None):
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])
        return 1, {self._meta.label: 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


class Organization(TimeStampedModel):
    class AccountType(models.TextChoices):
        PAYBILL = "PAYBILL", "Paybill"
        TILL = "TILL", "Buy Goods (Till)"

    class Environment(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        PRODUCTION = "production", "Production"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=60, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    county = models.CharField(max_length=80, blank=True)
    mpesa_shortcode = models.CharField(max_length=12, blank=True)
    mpesa_account_type = models.CharField(
        max_length=10, choices=AccountType.choices, default=AccountType.PAYBILL
    )
    mpesa_env = models.CharField(
        max_length=12, choices=Environment.choices, default=Environment.SANDBOX
    )
    sms_sender_id = models.CharField(max_length=20, blank=True)
    timezone = models.CharField(max_length=50, default="Africa/Nairobi")
    currency = models.CharField(max_length=3, default="KES")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGIN_FAILED = "LOGIN_FAILED", "Login failed"
        LOGOUT = "LOGOUT", "Logout"
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        RESTORE = "RESTORE", "Restore"
        PAYMENT_RECORDED = "PAYMENT_RECORDED", "Payment recorded"
        PAYMENT_REVERSED = "PAYMENT_REVERSED", "Payment reversed"
        PAYMENT_MATCHED = "PAYMENT_MATCHED", "Payment matched"
        LEDGER_POSTED = "LEDGER_POSTED", "Ledger posted"
        REMINDER_SENT = "REMINDER_SENT", "Reminder sent"
        STK_PUSH = "STK_PUSH", "STK push"
        MPESA_CALLBACK = "MPESA_CALLBACK", "M-Pesa callback"
        EXPORT = "EXPORT", "Export"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    model_name = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    prev_hash = models.CharField(max_length=64, blank=True)
    hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "action", "created_at"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.model_name}:{self.object_id}"

    def _compute_hash(self) -> str:
        payload = {
            "organization": str(self.organization_id or ""),
            "actor": str(self.actor_id or ""),
            "action": self.action,
            "model_name": self.model_name,
            "object_id": self.object_id,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "prev_hash": self.prev_hash,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("Audit log entries are immutable")
        if not self.created_at:
            self.created_at = timezone.now()
        if not self.prev_hash:
            last = (
                AuditLog.objects.filter(organization=self.organization)
                .order_by("-created_at")
                .first()
            )
            self.prev_hash = last.hash if last else ""
        self.hash = self._compute_hash()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted")

    @classmethod
    def record(
        cls,
        action,
        *,
        obj=None,
        organization=None,
        actor=None,
        changes=None,
        request=None,
    ):
        from apps.core.audit import get_current_request

        request = request or get_current_request()
        if request is not None:
            if actor is None and getattr(request, "user", None) and request.user.is_authenticated:
                actor = request.user
            ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
                "REMOTE_ADDR"
            )
            ua = request.META.get("HTTP_USER_AGENT", "")[:255]
        else:
            ip = None
            ua = ""

        if obj is not None:
            organization = organization or getattr(obj, "organization", None)
            model_name = obj._meta.label
            object_id = str(obj.pk)
            object_repr = str(obj)[:255]
        else:
            model_name = ""
            object_id = ""
            object_repr = ""

        return cls.objects.create(
            organization=organization,
            actor=actor if getattr(actor, "pk", None) else None,
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes or {},
            ip_address=ip,
            user_agent=ua,
        )
