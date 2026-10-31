from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.models import Organization
from apps.leases.models import Lease
from apps.properties.models import Property, Unit
from apps.tenants.models import Tenant


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="Acme Rentals",
        slug="acme",
        phone="254700000000",
        mpesa_shortcode="123456",
        mpesa_env="sandbox",
    )


@pytest.fixture
def other_org(db):
    return Organization.objects.create(
        name="Other Rentals",
        slug="other",
        phone="254700000001",
        mpesa_shortcode="654321",
    )


@pytest.fixture
def admin_user(db, org):
    return User.objects.create_user(
        email="admin@example.com",
        password="StrongPass123!",
        phone="0712345678",
        full_name="Admin User",
        role=User.Role.ADMIN,
        organization=org,
        is_staff=True,
    )


@pytest.fixture
def caretaker_user(db, org):
    return User.objects.create_user(
        email="caretaker@example.com",
        password="StrongPass123!",
        phone="0712345679",
        full_name="Caretaker User",
        role=User.Role.CARETAKER,
        organization=org,
    )


@pytest.fixture
def tenant_user(db, org):
    return User.objects.create_user(
        email="tenant@example.com",
        password="StrongPass123!",
        phone="0722000000",
        full_name="Jane Tenant",
        role=User.Role.TENANT,
        organization=org,
    )


@pytest.fixture
def tenant(db, org, tenant_user):
    return Tenant.objects.create(
        organization=org,
        user=tenant_user,
        full_name="Jane Tenant",
        phone="0722000000",
        email="tenant@example.com",
    )


@pytest.fixture
def other_tenant(db, other_org):
    return Tenant.objects.create(
        organization=other_org,
        full_name="Other Tenant",
        phone="0733000000",
    )


@pytest.fixture
def property_obj(db, org):
    return Property.objects.create(
        organization=org,
        name="Riverside Apartments",
        code="RIV",
        county="Nairobi",
    )


@pytest.fixture
def unit(db, property_obj):
    return Unit.objects.create(
        property=property_obj,
        code="A1",
        unit_type="2 Bedroom",
        default_rent=Decimal("10000.00"),
        status=Unit.Status.OCCUPIED,
    )


@pytest.fixture
def lease(db, org, unit, tenant):
    return Lease.objects.create(
        organization=org,
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 10, 1),
        rent_amount=Decimal("10000.00"),
        due_day=5,
        deposit_amount=Decimal("10000.00"),
        status=Lease.Status.ACTIVE,
    )
