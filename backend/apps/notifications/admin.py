from django.contrib import admin

from apps.notifications.models import (
    MessageLog,
    Notification,
    PromiseToPay,
    Reminder,
    ReminderSetting,
)


@admin.register(ReminderSetting)
class ReminderSettingAdmin(admin.ModelAdmin):
    list_display = ("organization", "enabled", "pre_due_days", "language", "send_hour")


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("tenant", "reminder_type", "scheduled_for", "status", "amount_due")
    list_filter = ("status", "reminder_type", "organization")
    search_fields = ("tenant__full_name", "tenant__phone")


@admin.register(PromiseToPay)
class PromiseToPayAdmin(admin.ModelAdmin):
    list_display = ("tenant", "amount", "promised_date", "status")
    list_filter = ("status", "organization")
    search_fields = ("tenant__full_name",)


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ("phone", "template", "status", "cost", "created_at")
    list_filter = ("status", "channel", "organization")
    search_fields = ("phone", "body")
    readonly_fields = [f.name for f in MessageLog._meta.fields]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "level", "read_at", "created_at")
    list_filter = ("level",)
    search_fields = ("title", "user__email")
