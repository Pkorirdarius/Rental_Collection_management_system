from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("full_name", "email")
    list_display = ("email", "full_name", "phone", "role", "organization", "is_active", "totp_enabled")
    list_filter = ("role", "is_active", "totp_enabled", "organization")
    search_fields = ("email", "phone", "full_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "phone", "role", "organization")}),
        ("Security", {"fields": ("totp_enabled", "must_change_password", "is_active", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone", "full_name", "role", "organization", "password1", "password2"),
            },
        ),
    )
