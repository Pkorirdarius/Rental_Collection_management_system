from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import AuditLog
from apps.leases.models import Lease
from apps.ledger.models import LedgerEntry
from apps.ledger.services import (
    apply_late_fees,
    generate_rent_charges,
    lease_balance,
    lease_statement,
    outstanding_charges,
    post_payment,
    post_reversal,
    prorated_rent,
)


@pytest.mark.django_db
def test_generate_rent_charges_is_idempotent(org, lease):
    first = generate_rent_charges(2026, 10, org)
    assert first["created"] == 1
    assert lease_balance(lease) == Decimal("10000.00")

    second = generate_rent_charges(2026, 10, org)
    assert second["created"] == 0
    assert second["skipped"] == 1
    assert lease_balance(lease) == Decimal("10000.00")


@pytest.mark.django_db
def test_payment_reduces_balance_and_reversal_restores_it(lease):
    generate_rent_charges(2026, 10, lease.organization)
    entry, created = post_payment(lease, amount=Decimal("4000.00"))
    assert created is True
    assert lease_balance(lease) == Decimal("6000.00")

    reversal, created = post_reversal(entry, reason="wrong tenant")
    assert created is True
    assert lease_balance(lease) == Decimal("10000.00")

    _, created_again = post_reversal(entry, reason="duplicate")
    assert created_again is False
    assert lease_balance(lease) == Decimal("10000.00")
    assert LedgerEntry.objects.filter(lease=lease).count() == 3


@pytest.mark.django_db
def test_outstanding_charges_uses_fifo_and_ageing(lease):
    generate_rent_charges(2026, 10, lease.organization)
    post_payment(lease, amount=Decimal("6000.00"), effective_date=date(2026, 10, 6))

    charges = outstanding_charges(lease, date(2026, 10, 10))
    assert len(charges) == 1
    assert charges[0]["remaining"] == Decimal("4000.00")
    assert charges[0]["due_date"] == date(2026, 10, 5)
    assert charges[0]["days_overdue"] == 5
    assert charges[0]["bucket"] == "1-7"


@pytest.mark.django_db
def test_proration_uses_days_occupied(org, unit, tenant):
    lease = Lease.objects.create(
        organization=org,
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 10, 15),
        rent_amount=Decimal("10000.00"),
        due_day=5,
        proration_enabled=True,
    )
    amount = prorated_rent(lease, date(2026, 10, 1), date(2026, 10, 31))
    assert amount == Decimal("5483.87")

    lease.proration_enabled = False
    lease.save(update_fields=["proration_enabled"])
    assert prorated_rent(lease, date(2026, 10, 1), date(2026, 10, 31)) == Decimal("10000.00")


@pytest.mark.django_db
def test_late_fee_is_applied_once(lease):
    lease.late_fee_type = Lease.LateFeeType.FLAT
    lease.late_fee_value = Decimal("500.00")
    lease.save(update_fields=["late_fee_type", "late_fee_value"])
    generate_rent_charges(2026, 10, lease.organization)

    result = apply_late_fees(lease.organization, today=date(2026, 10, 31))
    assert result["applied"] == 1
    assert lease_balance(lease) == Decimal("10500.00")

    again = apply_late_fees(lease.organization, today=date(2026, 10, 31))
    assert again["applied"] == 0
    assert lease_balance(lease) == Decimal("10500.00")


@pytest.mark.django_db
def test_statement_has_running_balance(lease):
    generate_rent_charges(2026, 10, lease.organization)
    post_payment(lease, amount=Decimal("2500.00"))
    statement = lease_statement(lease)
    assert statement["balance"] == "7500.00"
    assert len(statement["entries"]) == 2
    assert statement["entries"][-1]["balance"] == "7500.00"


@pytest.mark.django_db
def test_audit_log_is_immutable(org, admin_user):
    log = AuditLog.record(
        AuditLog.Action.CREATE,
        organization=org,
        actor=admin_user,
        changes={"test": True},
    )
    assert log.hash
    with pytest.raises(ValueError):
        log.save()
    with pytest.raises(ValueError):
        log.delete()
