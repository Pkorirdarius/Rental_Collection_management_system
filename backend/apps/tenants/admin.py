from django.contrib import admin

from apps.tenants.models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "organization", "status", "portal_enabled")
    list_filter = ("status", "organization")
    search_fields = ("full_name", "phone", "email")
