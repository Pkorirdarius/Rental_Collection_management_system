from django.contrib import admin

from apps.ledger.models import LedgerEntry


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("effective_date", "lease", "entry_type", "amount", "source", "created_at")
    list_filter = ("entry_type", "source", "organization")
    search_fields = ("lease__tenant__full_name", "description", "payment__reference")
    readonly_fields = [f.name for f in LedgerEntry._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
