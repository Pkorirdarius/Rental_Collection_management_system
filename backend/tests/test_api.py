from decimal import Decimal

import pytest

from apps.core.models import AuditLog
from apps.ledger.services import generate_rent_charges
from apps.payments.services import record_cash_payment
from apps.properties.models import PropertyAssignment


@pytest.mark.django_db
def test_login_with_email_and_phone(api_client, admin_user):
    by_email = api_client.post(
        "/api/v1/auth/login",
        {"identifier": "admin@example.com", "password": "StrongPass123!"},
        format="json",
    )
    assert by_email.status_code == 200
    assert by_email.json()["access"]
    assert by_email.json()["user"]["email"] == "admin@example.com"

    by_phone = api_client.post(
        "/api/v1/auth/login",
        {"identifier": "0712345678", "password": "StrongPass123!"},
        format="json",
    )
    assert by_phone.status_code == 200
    assert by_phone.json()["access"]


@pytest.mark.django_db
def test_login_rejects_bad_password(api_client, admin_user):
    response = api_client.post(
        "/api/v1/auth/login",
        {"identifier": "admin@example.com", "password": "wrong"},
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_properties_are_scoped_by_role(api_client, admin_user, caretaker_user, tenant_user, property_obj):
    PropertyAssignment.objects.create(user=caretaker_user, property=property_obj)

    api_client.force_authenticate(user=admin_user)
    assert api_client.get("/api/v1/properties/").status_code == 200
    assert len(api_client.get("/api/v1/properties/").json()["results"]) == 1

    api_client.force_authenticate(user=caretaker_user)
    caretaker_rows = api_client.get("/api/v1/properties/").json()["results"]
    assert len(caretaker_rows) == 1

    api_client.force_authenticate(user=tenant_user)
    assert api_client.get("/api/v1/properties/").status_code == 403


@pytest.mark.django_db
def test_tenant_cannot_list_tenants(api_client, tenant_user):
    api_client.force_authenticate(user=tenant_user)
    assert api_client.get("/api/v1/tenants/").status_code == 403


@pytest.mark.django_db
def test_tenant_portal_shows_only_own_data(api_client, tenant_user, tenant, lease, other_tenant):
    generate_rent_charges(2026, 10, lease.organization)
    record_cash_payment(
        organization=lease.organization,
        tenant=tenant,
        amount=Decimal("2000.00"),
    )

    api_client.force_authenticate(user=tenant_user)
    profile = api_client.get("/api/v1/portal/me")
    assert profile.status_code == 200
    assert profile.json()["id"] == str(tenant.id)
    assert profile.json()["balance"] == "8000.00"

    payments = api_client.get("/api/v1/portal/me/payments").json()
    assert len(payments) == 1
    assert all(row["tenant"] == str(tenant.id) for row in payments)

    other_user = other_tenant
    assert other_user.id != tenant.id


@pytest.mark.django_db
def test_dashboard_requires_admin(api_client, admin_user, tenant_user, lease):
    generate_rent_charges(2026, 10, lease.organization)
    api_client.force_authenticate(user=admin_user)
    response = api_client.get("/api/v1/dashboard/summary?month=2026-10")
    assert response.status_code == 200
    assert "collected" in response.json()

    api_client.force_authenticate(user=tenant_user)
    assert api_client.get("/api/v1/dashboard/summary").status_code == 403


@pytest.mark.django_db
def test_tenant_statement_pdf(api_client, admin_user, tenant, lease):
    generate_rent_charges(2026, 10, lease.organization)
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(f"/api/v1/tenants/{tenant.id}/statement-pdf/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_audit_log_list(api_client, admin_user, org):
    AuditLog.record(AuditLog.Action.CREATE, organization=org, actor=admin_user, changes={"x": 1})
    api_client.force_authenticate(user=admin_user)
    response = api_client.get("/api/v1/audit-logs/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["action"] == AuditLog.Action.CREATE


@pytest.mark.django_db
def test_health_endpoint(api_client):
    response = api_client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
