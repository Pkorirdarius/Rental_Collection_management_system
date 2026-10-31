"""Central helpers that enforce organization and caretaker property scoping."""

from django.db.models import Q


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.is_admin)


def is_caretaker(user) -> bool:
    return bool(user and user.is_authenticated and user.is_caretaker)


def is_tenant(user) -> bool:
    return bool(user and user.is_authenticated and user.is_tenant)


def assigned_property_ids(user):
    from apps.properties.models import PropertyAssignment

    return PropertyAssignment.objects.filter(user=user).values_list("property_id", flat=True)


def scope_org(queryset, user):
    """Admins see their organization; everyone else sees nothing by default."""
    if not user or not user.is_authenticated or not user.organization_id:
        return queryset.none()
    return queryset.filter(organization_id=user.organization_id)


def scope_property_queryset(queryset, user, property_path="property"):
    if is_admin(user):
        return scope_org(queryset, user)
    if is_caretaker(user):
        return scope_org(queryset, user).filter(
            **{f"{property_path}__in": assigned_property_ids(user)}
        )
    return queryset.none()


def scope_tenant_queryset(queryset, user, tenant_path="tenant"):
    if is_admin(user):
        return scope_org(queryset, user)
    if is_caretaker(user):
        return scope_org(queryset, user).filter(
            **{
                f"{tenant_path}__leases__unit__property__in": assigned_property_ids(user),
                f"{tenant_path}__leases__status": "ACTIVE",
            }
        ).distinct()
    if is_tenant(user):
        return scope_org(queryset, user).filter(**{tenant_path: user.tenant_profile})
    return queryset.none()


def scope_lease_queryset(queryset, user):
    if is_admin(user):
        return scope_org(queryset, user)
    if is_caretaker(user):
        return scope_org(queryset, user).filter(
            unit__property__in=assigned_property_ids(user)
        )
    if is_tenant(user):
        return scope_org(queryset, user).filter(tenant__user=user)
    return queryset.none()


def scope_payment_queryset(queryset, user):
    if is_admin(user):
        return scope_org(queryset, user)
    if is_caretaker(user):
        return scope_org(queryset, user).filter(
            unit__property__in=assigned_property_ids(user)
        )
    if is_tenant(user):
        return scope_org(queryset, user).filter(tenant__user=user)
    return queryset.none()


def scope_tenant_record(queryset, user):
    if is_admin(user):
        return scope_org(queryset, user)
    if is_caretaker(user):
        return scope_org(queryset, user).filter(
            Q(leases__unit__property__in=assigned_property_ids(user))
        ).distinct()
    if is_tenant(user):
        return scope_org(queryset, user).filter(user=user)
    return queryset.none()
