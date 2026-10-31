from django.contrib import admin

from apps.leases.models import Lease


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ("tenant", "unit", "rent_amount", "due_day", "status", "start_date", "end_date")
    list_filter = ("status", "organization")
    search_fields = ("tenant__full_name", "tenant__phone", "unit__code")
    raw_id_fields = ("unit", "tenant")
