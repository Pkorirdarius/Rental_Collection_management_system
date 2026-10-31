from django.contrib import admin

from apps.payments.models import (
    MpesaCallbackLog,
    MpesaRequest,
    Payment,
    PaymentEvent,
    Receipt,
    ReceiptSequence,
    ReconciliationRun,
)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "tenant", "amount", "method", "status", "paid_at", "organization")
    list_filter = ("method", "status", "organization")
    search_fields = ("reference", "provider_txn_id", "tenant__full_name", "phone")
    readonly_fields = [f.name for f in Payment._meta.fields]


@admin.register(MpesaRequest)
class MpesaRequestAdmin(admin.ModelAdmin):
    list_display = ("checkout_request_id", "phone", "amount", "status", "purpose", "created_at")
    list_filter = ("status", "purpose")
    search_fields = ("checkout_request_id", "mpesa_receipt", "phone")
    readonly_fields = [f.name for f in MpesaRequest._meta.fields]


@admin.register(MpesaCallbackLog)
class MpesaCallbackLogAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "created_at", "processed", "ip_address")
    list_filter = ("endpoint", "processed")
    readonly_fields = [f.name for f in MpesaCallbackLog._meta.fields]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("number", "payment", "issued_at", "sms_sent")
    search_fields = ("number", "payment__reference")
    readonly_fields = [f.name for f in Receipt._meta.fields]


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(admin.ModelAdmin):
    list_display = ("started_at", "finished_at", "checked", "matched", "unmatched", "errors")
    readonly_fields = [f.name for f in ReconciliationRun._meta.fields]


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("payment", "event", "created_at")
    readonly_fields = [f.name for f in PaymentEvent._meta.fields]


admin.site.register(ReceiptSequence)
