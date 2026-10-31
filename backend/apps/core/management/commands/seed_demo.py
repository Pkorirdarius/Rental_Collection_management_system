from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import AuditLog, Organization
from apps.leases.models import Lease
from apps.ledger.models import LedgerEntry
from apps.ledger.services import (
    add_months,
    days_overdue,
    generate_rent_charges,
    lease_balance,
)
from apps.notifications.models import (
    MessageLog,
    Notification,
    PromiseToPay,
    Reminder,
    ReminderSetting,
)
from apps.notifications.templates import render
from apps.payments.models import (
    MpesaCallbackLog,
    MpesaRequest,
    Payment,
    PaymentEvent,
    Receipt,
    ReceiptSequence,
    ReconciliationRun,
)
from apps.payments.services import ingest_mpesa_payment, record_cash_payment
from apps.properties.models import Property, PropertyAssignment, Unit
from apps.tenants.models import Tenant

ORG_SLUG = "kwanjuguna"
PASSWORD = "Demo12345!"

PROPERTIES = (
    (
        "KIL",
        "Kilimani Heights",
        "Ngong Road",
        "Nairobi",
        "Nairobi",
        (
            ("A1", "2 Bedroom", 2, "35000.00", "70000.00"),
            ("A2", "2 Bedroom", 2, "40000.00", "80000.00"),
            ("A3", "3 Bedroom", 3, "55000.00", "110000.00"),
            ("A4", "Studio", 1, "25000.00", "50000.00"),
        ),
    ),
    (
        "RUA",
        "Ruaka Court",
        "Limuru Road",
        "Ruaka",
        "Kiambu",
        (
            ("B1", "1 Bedroom", 1, "18000.00", "36000.00"),
            ("B2", "1 Bedroom", 1, "20000.00", "40000.00"),
            ("B3", "2 Bedroom", 2, "28000.00", "56000.00"),
            ("B4", "Bedsitter", 1, "14000.00", "28000.00"),
        ),
    ),
    (
        "WST",
        "Westlands Suites",
        "Waiyaki Way",
        "Nairobi",
        "Nairobi",
        (
            ("C1", "3 Bedroom", 3, "65000.00", "130000.00"),
            ("C2", "2 Bedroom", 2, "50000.00", "100000.00"),
            ("C3", "Penthouse", 3, "90000.00", "180000.00"),
            ("C4", "Studio", 1, "32000.00", "64000.00"),
        ),
    ),
)

TENANTS = (
    ("Grace Wanjiku", "grace@demo.rent", "254711000001", "KIL-A1"),
    ("Peter Otieno", "peter@demo.rent", "254711000002", "KIL-A2"),
    ("Mary Njeri", "mary@demo.rent", "254711000003", "RUA-B1"),
    ("John Kamau", "john@demo.rent", "254711000004", "RUA-B2"),
    ("Faith Achieng", "faith@demo.rent", "254711000005", "WST-C1"),
    ("David Mwangi", "david@demo.rent", "254711000006", "WST-C2"),
)

PAYMENT_PLANS = {
    0: ("cash", 99, False),
    1: ("mpesa", 4, False),
    2: ("cash", 3, False),
    3: ("none", 0, False),
    4: ("mpesa", 99, False),
    5: ("cash", 5, True),
}


def _payment_time(day):
    day = min(day, timezone.localdate())
    naive = datetime.combine(day, time(10, 0))
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _ensure_user(*, email, phone, full_name, role, organization, password=PASSWORD):
    user = User.objects.filter(email=email).first() or User(email=email)
    user.phone = phone
    user.full_name = full_name
    user.role = role
    user.organization = organization
    user.is_active = True
    user.set_password(password)
    user.save()
    return user


class Command(BaseCommand):
    help = "Create a realistic demo landlord, properties, tenants, leases, payments and reminders."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Remove existing demo data first.")
        parser.add_argument("--months", type=int, default=6, help="Months of rent history to seed.")
        parser.add_argument("--password", default=PASSWORD, help="Password for all demo accounts.")

    def handle(self, *args, **options):
        months = max(1, options["months"])
        password = options["password"]
        org = Organization.objects.filter(slug=ORG_SLUG).first()

        if options["reset"] and org is not None:
            self._reset(org)
            org = None

        if org is None:
            org = Organization.objects.create(
                name="Kwa Njuguna Properties",
                slug=ORG_SLUG,
                phone="254700000001",
                email="hello@demo.rent",
                county="Nairobi",
                mpesa_shortcode="174379",
                mpesa_account_type=Organization.AccountType.PAYBILL,
                mpesa_env=Organization.Environment.SANDBOX,
                sms_sender_id="RENTDEMO",
                timezone="Africa/Nairobi",
                currency="KES",
            )
        else:
            org.mpesa_shortcode = org.mpesa_shortcode or "174379"
            org.save(update_fields=["mpesa_shortcode", "updated_at"])

        admin = _ensure_user(
            email="admin@demo.rent",
            phone="254700000001",
            full_name="Njuguna Kamau",
            role=User.Role.ADMIN,
            organization=org,
            password=password,
        )
        caretaker = _ensure_user(
            email="caretaker@demo.rent",
            phone="254700000002",
            full_name="Samuel Ochieng",
            role=User.Role.CARETAKER,
            organization=org,
            password=password,
        )

        today = timezone.localdate()
        current_month = today.replace(day=1)
        first_month = add_months(current_month, -(months - 1))
        lease_start = first_month + timedelta(days=2)

        properties: dict[str, Property] = {}
        units: dict[str, Unit] = {}
        for code, name, address, city, county, unit_rows in PROPERTIES:
            prop, _ = Property.objects.update_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "address": address,
                    "city": city,
                    "county": county,
                    "is_active": True,
                },
            )
            properties[code] = prop
            PropertyAssignment.objects.get_or_create(user=caretaker, property=prop)
            for unit_code, unit_type, bedrooms, rent, deposit in unit_rows:
                unit, _ = Unit.objects.update_or_create(
                    property=prop,
                    code=unit_code,
                    defaults={
                        "unit_type": unit_type,
                        "bedrooms": bedrooms,
                        "default_rent": Decimal(rent),
                        "default_deposit": Decimal(deposit),
                        "status": Unit.Status.VACANT,
                    },
                )
                units[f"{code}-{unit_code}"] = unit

        leases: list[Lease] = []
        tenants: list[Tenant] = []
        for index, (full_name, email, phone, unit_key) in enumerate(TENANTS):
            tenant_user = _ensure_user(
                email=email,
                phone=phone,
                full_name=full_name,
                role=User.Role.TENANT,
                organization=org,
                password=password,
            )
            tenant, _ = Tenant.objects.update_or_create(
                organization=org,
                phone=phone,
                defaults={
                    "user": tenant_user,
                    "full_name": full_name,
                    "email": email,
                    "status": Tenant.Status.ACTIVE,
                },
            )
            tenants.append(tenant)

            unit = units[unit_key]
            lease = Lease.objects.filter(unit=unit, status=Lease.Status.ACTIVE).first()
            if lease is None:
                lease = Lease(unit=unit, tenant=tenant, organization=org)
            lease.tenant = tenant
            lease.start_date = lease_start
            lease.end_date = None
            lease.rent_amount = unit.default_rent
            lease.due_day = 5
            lease.grace_period_days = 5
            lease.deposit_amount = unit.default_deposit
            lease.deposit_paid = unit.default_deposit
            lease.late_fee_type = Lease.LateFeeType.PERCENT if index == 2 else Lease.LateFeeType.FLAT
            lease.late_fee_value = Decimal("5.00") if index == 2 else Decimal("500.00")
            lease.late_fee_applies_after_grace = True
            lease.proration_enabled = index == 0
            lease.status = Lease.Status.ACTIVE
            lease.created_by = admin
            lease.save()
            leases.append(lease)

            Unit.objects.filter(pk=unit.pk).update(status=Unit.Status.OCCUPIED)

        for offset in range(months - 1, -1, -1):
            period = add_months(current_month, -offset)
            generate_rent_charges(period.year, period.month, organization=org)

        receipt_counter = 0
        for index, lease in enumerate(leases):
            method, full_count, partial = PAYMENT_PLANS[index]
            if method == "none":
                continue
            charges = list(
                LedgerEntry.objects.filter(
                    lease=lease, entry_type=LedgerEntry.Type.RENT_CHARGE
                ).order_by("effective_date")
            )
            payments = charges[:full_count]
            if partial and full_count < len(charges):
                payments.append(charges[full_count])
            for charge_index, charge in enumerate(payments):
                amount = charge.amount
                if partial and charge_index == len(payments) - 1:
                    amount = (amount / Decimal("2")).quantize(Decimal("0.01"))
                paid_at = _payment_time(charge.effective_date + timedelta(days=4))
                if method == "cash":
                    record_cash_payment(
                        organization=org,
                        tenant=lease.tenant,
                        lease=lease,
                        amount=amount,
                        paid_at=paid_at,
                        received_by=caretaker,
                        created_by=admin,
                        note=f"Demo cash payment for {charge.description}",
                        idempotency_key=f"seed:cash:{lease.id}:{charge.id}",
                    )
                else:
                    receipt_counter += 1
                    ingest_mpesa_payment(
                        receipt=f"SEEDMP{receipt_counter:05d}",
                        amount=amount,
                        phone=lease.tenant.phone,
                        bill_ref=lease.unit.mpesa_bill_ref,
                        shortcode=org.mpesa_shortcode,
                        paid_at=paid_at,
                        raw_payload={"seed": True, "charge": str(charge.id)},
                    )

        ingest_mpesa_payment(
            receipt="SEEDUNMATCHED1",
            amount=Decimal("5000.00"),
            phone="254799999999",
            bill_ref="UNKNOWN",
            shortcode=org.mpesa_shortcode,
            paid_at=_payment_time(today),
            raw_payload={"seed": True, "note": "Unmatched demo payment"},
        )

        PromiseToPay.objects.get_or_create(
            lease=leases[3],
            promised_date=today + timedelta(days=7),
            defaults={
                "organization": org,
                "tenant": leases[3].tenant,
                "amount": lease_balance(leases[3]),
                "note": "Waiting for salary on Friday.",
                "created_by": caretaker,
            },
        )

        setting = ReminderSetting.get_for_org(org)
        setting.sender_id = "RENTDEMO"
        setting.save(update_fields=["sender_id", "updated_at"])
        self._seed_reminders(org, leases, setting)

        Notification.objects.get_or_create(
            user=admin,
            title="Welcome to Rent Manager",
            defaults={
                "organization": org,
                "body": "Your demo portfolio is ready. Review overdue tenants and recent payments.",
                "level": "success",
                "link": "/dashboard",
            },
        )
        for tenant in tenants[:3]:
            if tenant.user_id:
                Notification.objects.get_or_create(
                    user=tenant.user,
                    title="Your tenant portal is ready",
                    defaults={
                        "organization": org,
                        "body": "View your balance, receipts and pay rent via M-Pesa.",
                        "level": "info",
                        "link": "/portal",
                    },
                )

        total_billed = sum(lease_balance(lease) for lease in leases)
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"  Organization: {org.name} ({org.slug})")
        self.stdout.write(f"  Properties: {len(properties)} | Units: {len(units)} | Tenants: {len(tenants)}")
        self.stdout.write(f"  Outstanding demo balance: KES {total_billed:,.2f}")
        self.stdout.write("  Logins:")
        self.stdout.write(f"    Admin:      admin@demo.rent / {password}")
        self.stdout.write(f"    Caretaker:  caretaker@demo.rent / {password}")
        self.stdout.write(f"    Tenant:     grace@demo.rent / {password}")

    def _seed_reminders(self, org, leases, setting):
        now = timezone.now()
        specs = (
            (1, Reminder.Type.DUE, Reminder.Status.SENT),
            (2, "OVERDUE_7", Reminder.Status.SENT),
            (3, "OVERDUE_14", Reminder.Status.SENT),
            (3, "OVERDUE_30", Reminder.Status.PENDING),
            (5, "OVERDUE_30", Reminder.Status.PENDING),
        )
        for lease_index, reminder_type, status in specs:
            lease = leases[lease_index]
            period_key = f"{timezone.localdate():%Y-%m}-{reminder_type}"
            if reminder_type == Reminder.Type.DUE:
                period_key = f"{timezone.localdate():%Y-%m}"
            key = "overdue" if str(reminder_type).startswith("OVERDUE") else "due"
            due = lease.due_date_for(timezone.localdate().replace(day=1))
            message = render(
                setting.language,
                key,
                name=lease.tenant.full_name.split(" ")[0],
                amount=lease_balance(lease),
                unit=lease.unit.code,
                property=lease.unit.property.name,
                due_date=due.strftime("%d %b %Y"),
                days=days_overdue(lease),
                shortcode=org.mpesa_shortcode or "your paybill",
                bill_ref=lease.unit.mpesa_bill_ref,
            )
            reminder, created = Reminder.objects.get_or_create(
                lease=lease,
                reminder_type=reminder_type,
                period_key=period_key,
                defaults={
                    "organization": org,
                    "tenant": lease.tenant,
                    "scheduled_for": timezone.localdate(),
                    "amount_due": lease_balance(lease),
                    "days_overdue": days_overdue(lease),
                    "message": message,
                },
            )
            if status == Reminder.Status.SENT and reminder.status != Reminder.Status.SENT:
                reminder.status = Reminder.Status.SENT
                reminder.sent_at = now
                reminder.save(update_fields=["status", "sent_at", "updated_at"])

    @transaction.atomic
    def _reset(self, org):
        LedgerEntry.objects.filter(organization=org).delete()
        Receipt.objects.filter(organization=org).delete()
        PaymentEvent.objects.filter(payment__organization=org).delete()
        MpesaRequest.objects.filter(organization=org).delete()
        ReconciliationRun.objects.filter(organization=org).delete()
        MpesaCallbackLog.objects.filter(organization=org).delete()
        Payment.objects.filter(organization=org).delete()
        Reminder.objects.filter(organization=org).delete()
        MessageLog.objects.filter(organization=org).delete()
        PromiseToPay.objects.filter(organization=org).delete()
        Notification.objects.filter(organization=org).delete()
        ReminderSetting.objects.filter(organization=org).delete()
        Lease.all_objects.filter(organization=org).delete()
        Tenant.all_objects.filter(organization=org).delete()
        PropertyAssignment.objects.filter(property__organization=org).delete()
        Unit.all_objects.filter(organization=org).delete()
        Property.all_objects.filter(organization=org).delete()
        ReceiptSequence.objects.filter(organization=org).delete()
        AuditLog.objects.filter(organization=org).delete()
        User.objects.filter(organization=org).delete()
        org.delete()
