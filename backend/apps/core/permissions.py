from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    message = "Only the landlord/admin can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsAdminOrCaretaker(BasePermission):
    message = "Only staff can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_admin or request.user.is_caretaker)
        )


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_admin


class IsAdminOrCaretakerReadOnly(BasePermission):
    """Caretakers can read and record payments, but cannot mutate master data."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_admin:
            return True
        if request.user.is_caretaker and request.method in SAFE_METHODS:
            return True
        return False


class IsTenantSelf(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_tenant)

    def has_object_permission(self, request, view, obj):
        tenant = getattr(obj, "tenant", obj)
        return getattr(tenant, "user_id", None) == request.user.id
