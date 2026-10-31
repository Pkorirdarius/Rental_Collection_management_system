from django.contrib import admin

from apps.properties.models import Property, PropertyAssignment, Unit


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "county", "is_active", "organization")
    list_filter = ("is_active", "county")
    search_fields = ("name", "code", "address")
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("__str__", "property", "status", "default_rent", "mpesa_bill_ref")
    list_filter = ("status", "property")
    search_fields = ("code", "mpesa_bill_ref")


@admin.register(PropertyAssignment)
class PropertyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "property", "created_at")
    search_fields = ("user__full_name", "property__name")
