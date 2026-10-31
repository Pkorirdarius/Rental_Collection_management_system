from decimal import Decimal

import pytest

from apps.ledger.services import generate_rent_charges, lease_balance
from apps.payments.models import Payment
from apps.payments.services import (
    ingest_mpesa_payment,
    match_payment,
    record_cash_payment,
    reverse_payment,
)


@pytest.mark.django_db
def test_cash_payment_creates_ledger_entry_and_receipt(org, tenant, lease, admin_user):
    generate_rent_charges(2026, 10, org)
    payment, receipt = record_cash_payment(
        organization=org,
        tenant=tenant,
        amount=Decimal("5000.00"),
        received_by=admin_user,
        created_by=admin_user,
    )
    assert payment.status == Payment.Status.CONFIRMED
    assert receipt.number.startswith("RCPT-ACME-")
    assert payment.receipt == receipt
    assert receipt.pdf_file
    assert lease_balance(lease) == Decimal("5000.00")
    assert payment.ledger_entries.count() == 1


@pytest.mark.django_db
def test_cash_payment_idempotency(org, tenant, lease, admin_user):
    generate_rent_charges(2026, 10, org)
    first, _ = record_cash_payment(
        organization=org,
        tenant=tenant,
        amount=Decimal("3000.00"),
        received_by=admin_user,
        idempotency_key="cash-1",
    )
    second, _ = record_cash_payment(
        organization=org,
        tenant=tenant,
        amount=Decimal("3000.00"),
        received_by=admin_user,
        idempotency_key="cash-1",
    )
    assert first.id == second.id
    assert Payment.objects.count() == 1
    assert lease_balance(lease) == Decimal("7000.00")


@pytest.mark.django_db
def test_mpesa_payment_matches_bill_ref_and_is_idempotent(org, tenant, lease, unit):
    generate_rent_charges(2026, 10, org)
    payment, created = ingest_mpesa_payment(
        receipt="ABC123XYZ",
        amount="10000.00",
        phone=tenant.phone,
        bill_ref=unit.mpesa_bill_ref,
        shortcode=org.mpesa_shortcode,
    )
    assert created is True
    assert payment.status == Payment.Status.CONFIRMED
    assert payment.lease == lease
    assert payment.receipt.number
    assert lease_balance(lease) == Decimal("0.00")

    duplicate, created_again = ingest_mpesa_payment(
        receipt="ABC123XYZ",
        amount="10000.00",
        phone=tenant.phone,
        bill_ref=unit.mpesa_bill_ref,
        shortcode=org.mpesa_shortcode,
    )
    assert created_again is False
    assert duplicate.id == payment.id
    assert Payment.objects.count() == 1


@pytest.mark.django_db
def test_unknown_mpesa_payment_is_unmatched_and_can_be_matched(org, lease, admin_user):
    generate_rent_charges(2026, 10, org)
    payment, created = ingest_mpesa_payment(
        receipt="UNKNOWN1",
        amount="1500.00",
        phone="0700000000",
        bill_ref="NO-SUCH-REF",
        shortcode=org.mpesa_shortcode,
    )
    assert created is True
    assert payment.status == Payment.Status.UNMATCHED
    assert payment.lease is None
    assert lease_balance(lease) == Decimal("10000.00")

    matched = match_payment(payment, lease=lease, actor=admin_user, note="verified")
    assert matched.status == Payment.Status.CONFIRMED
    assert matched.lease == lease
    assert matched.receipt.number
    assert lease_balance(lease) == Decimal("8500.00")


@pytest.mark.django_db
def test_mpesa_payment_with_wrong_shortcode_is_unmatched(org, tenant, lease, unit):
    generate_rent_charges(2026, 10, org)
    payment, _ = ingest_mpesa_payment(
        receipt="WRONGCODE1",
        amount="10000.00",
        phone=tenant.phone,
        bill_ref=unit.mpesa_bill_ref,
        shortcode="999999",
    )
    assert payment.status == Payment.Status.UNMATCHED
    assert lease_balance(lease) == Decimal("10000.00")


@pytest.mark.django_db
def test_reverse_payment_restores_balance(org, tenant, lease, admin_user):
    generate_rent_charges(2026, 10, org)
    payment, _ = record_cash_payment(
        organization=org,
        tenant=tenant,
        amount=Decimal("4000.00"),
        received_by=admin_user,
    )
    assert lease_balance(lease) == Decimal("6000.00")

    reversals = reverse_payment(payment, reason="bounced", actor=admin_user)
    payment.refresh_from_db()
    assert payment.status == Payment.Status.REVERSED
    assert len(reversals) == 1
    assert lease_balance(lease) == Decimal("10000.00")


@pytest.mark.django_db
def test_c2b_webhook_requires_token_and_records_payment(api_client, org, tenant, lease, unit):
    generate_rent_charges(2026, 10, org)
    payload = {
        "TransID": "WEBHOOK1",
        "TransAmount": "10000.00",
        "BusinessShortCode": org.mpesa_shortcode,
        "BillRefNumber": unit.mpesa_bill_ref,
        "MSISDN": tenant.phone,
    }
    rejected = api_client.post("/api/v1/webhooks/mpesa/c2b/confirmation", payload, format="json")
    assert rejected.status_code == 403

    accepted = api_client.post(
        "/api/v1/webhooks/mpesa/c2b/confirmation?token=test-token",
        payload,
        format="json",
    )
    assert accepted.status_code == 200
    assert accepted.json()["ResultCode"] == 0
    payment = Payment.objects.get(reference="WEBHOOK1")
    assert payment.status == Payment.Status.CONFIRMED
    assert lease_balance(lease) == Decimal("0.00")


@pytest.mark.django_db
def test_cash_payment_api_permissions_and_flow(api_client, admin_user, tenant, lease):
    generate_rent_charges(2026, 10, lease.organization)
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(
        "/api/v1/payments/cash",
        {"tenant": str(tenant.id), "amount": "2500.00"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["receipt_number"].startswith("RCPT-")
    assert lease_balance(lease) == Decimal("7500.00")

    api_client.force_authenticate(user=tenant.user)
    forbidden = api_client.post(
        "/api/v1/payments/cash",
        {"tenant": str(tenant.id), "amount": "100.00"},
        format="json",
    )
    assert forbidden.status_code == 403
