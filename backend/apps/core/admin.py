from django.contrib import admin

from apps.core.models import AuditLog, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "mpesa_shortcode", "mpesa_env", "is_active")
    search_fields = ("name", "slug", "mpesa_shortcode")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "model_name", "object_id", "actor")
    list_filter = ("action", "model_name")
    search_fields = ("object_id", "object_repr", "actor__email")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
