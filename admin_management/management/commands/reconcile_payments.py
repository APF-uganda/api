"""
Management command to reconcile payments from the official APF members register.

Creates verified ManualPayment records for:
  - Application fee (UGX 50,000) for every member in the register
  - Renewal fee (UGX 150,000) for members who have paid it

Members not found in the system are skipped and reported.
Existing verified records are never duplicated.

Usage:
  python manage.py reconcile_payments --dry-run   # preview, no changes
  python manage.py reconcile_payments             # apply
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

APP_FEE     = Decimal('50000.00')
RENEWAL_FEE = Decimal('150000.00')

# ── Official members register as at 4th February 2026 ────────────────────────
# (email, paid_renewal)  — everyone paid the 50k app fee
# renewal=True means they also paid the 150k renewal
MEMBERS_REGISTER = [
    ("kherman32@gmail.com",             False),
    ("patrickmugarura10@yahoo.com",     False),
    ("gkkakala@gmail.com",              False),   # renewal was 50k in source — treated as no renewal
    ("constant.mayende@gmail.com",      True),
    ("r.albert.otete@gmail.com",        False),
    ("maria@springstugye.com",          False),
    ("nuwamanyageoffrey@gmail.com",     False),
    ("rmutumba@mutumbamukobe.org",      False),
    ("emojongodeke@gmail.com",          False),
    ("mante@continentalpartners.org",   True),   # David Nyende primary email
    ("gard662@gmail.com",               True),   # David Nyende secondary — create if found
    ("justin@osillocpa.com",            False),
    ("senogaassociates@gmail.com",      False),
    ("michael@springstugye.com",        False),
    ("a.arnold@ardenfield.com",         False),
    ("a.dennis@ardenfield.com",         False),
    ("pius.ssuuna@gmail.com",           False),
    ("rhodaochan@gmail.com",            False),
    ("annetnantumbwe1@gmail.com",       False),
    ("ochanbernard@gmail.com",          False),
    ("sekiziyivuissa@gmail.com",        False),
    ("msilverboss@gmail.com",           False),
    ("muke280@gmail.com",               False),
    ("lmawanda45@gmail.com",            False),
    ("kalindaassociates@gmail.com",     False),
    ("chrisnet4@gmail.com",             False),
    ("info@pepartnersuganda.com",       True),
    ("jay.oriekot@gmail.com",           False),
    ("rwomus.stepehn@gmail.com",        False),
    ("annerozbob1@gmail.com",           False),
    ("abdul@springstugye.com",          False),
    ("pkbanadda@gmail.com",             False),
    ("woodhask.ediomu@woodhask.com",    False),
    ("biz.bizandcompany@gmail.com",     True),
    ("glutwama@gmail.com",              False),
    ("dssebugwawo@gmail.com",           False),
    ("arch.archelia@gmail.com",         False),
    ("kabuchualfred@gmail.com",         False),
    ("jbmwanja@gmail.com",              False),
    ("gadzk@yahoo.com",                 False),
    ("otimotile@yahoo.com",             False),
    ("rmatsiko89@gmail.com",            False),
    ("davidssenoga@gmail.com",          True),   # fixed typo: gmail,com → gmail.com
    ("bwireb@gmail.com",                False),
    ("thomsonkwizina@gmail.com",        False),
    ("mwagodassociates@gmail.com",      False),
    ("jamiekasule@yahoo.com",           False),
    ("peterkasango1@gmail.com",         True),
    ("marknsubugacpa@gmail.com",        False),
    ("rwebishugi@gmail.com",            False),
    ("basiima55@yahoo.co.uk",           False),
    ("fmtwine@gmail.com",               False),
    ("kasawulibaker@gmail.com",         True),
    ("rkyalimpa@gmail.com",             False),
    ("manyiredith@gmail.com",           True),
    ("sgabula2001@yahoo.co.uk",         False),
    # Rows 55, 57-60: no email — skipped
]


def _get_or_create_stub_application(user, registered_by):
    """
    Returns the member's application if one exists, otherwise creates a minimal
    stub application so we have something to attach the ManualPayment FK to.
    """
    from applications.models import Application
    app = Application.objects.filter(email__iexact=user.email).order_by('-submitted_at').first()
    if app:
        return app
    # Create a minimal stub — status approved, no payment info
    return Application.objects.create(
        email=user.email,
        username=user.email.split('@')[0],
        password_hash='',
        first_name=user.first_name or '',
        last_name=user.last_name or '',
        age_range='',
        phone_number=user.phone_number or '',
        address='',
        payment_method='bank',
        status='approved',
        payment_status='success',
        user=user,
    )


def _ensure_payment(user, application, amount, description, payment_type,
                    registered_by, note, dry_run, stdout, style):
    """
    Creates a verified ManualPayment if one doesn't already exist for this
    user / payment_type / amount combination.
    Returns 'created', 'exists', or 'dry_created'.
    """
    from payments.models import ManualPayment

    existing = ManualPayment.objects.filter(
        user=user,
        payment_type=payment_type,
        amount=amount,
        status=ManualPayment.STATUS_VERIFIED,
    ).first()

    if existing:
        return 'exists'

    label = f'UGX {int(amount):,}  {description}'
    if dry_run:
        stdout.write(style.SUCCESS(f'  [DRY] Would create {label}  →  {user.email}'))
        return 'dry_created'

    ManualPayment.objects.create(
        application=application,
        user=user,
        amount=amount,
        currency='UGX',
        reference=f'REGISTER-{payment_type.upper()[:3]}-{user.email}',
        description=description,
        payment_type=payment_type,
        status=ManualPayment.STATUS_VERIFIED,
        verified_by=registered_by,
        verified_at=timezone.now(),
        verification_notes=note,
        proof_of_payment='',
    )
    stdout.write(style.SUCCESS(f'  ✓  Created {label}  →  {user.email}'))
    return 'created'


class Command(BaseCommand):
    help = 'Reconcile payment statuses from the official APF members register (Feb 2026)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
            help='Preview changes without writing to the database')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  ⚠️  DRY RUN — no changes will be made\n'))

        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS('  RECONCILE PAYMENTS — APF Members Register Feb 2026'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))

        # Use the first admin as the verifier
        admin = User.objects.filter(role='1').order_by('id').first()
        note = 'Back-filled from official APF members register (Feb 2026) via reconcile_payments command'

        not_found      = []
        app_created    = app_exists    = 0
        renew_created  = renew_exists  = 0

        with transaction.atomic():
            for email, paid_renewal in MEMBERS_REGISTER:
                email = email.lower().strip()
                user = User.objects.filter(email__iexact=email).first()

                if not user:
                    not_found.append(email)
                    self.stdout.write(self.style.WARNING(f'  ⚠  NOT FOUND  {email}'))
                    continue

                # Get or create application stub
                try:
                    application = _get_or_create_stub_application(user, admin)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗  Could not get/create application for {email}: {e}'))
                    continue

                # ── Application fee ──────────────────────────────────────────
                result = _ensure_payment(
                    user=user, application=application,
                    amount=APP_FEE,
                    description='Application Fee',
                    payment_type='membership_renewal',
                    registered_by=admin,
                    note=note,
                    dry_run=dry_run,
                    stdout=self.stdout, style=self.style,
                )
                if result == 'exists':
                    self.stdout.write(f'  –  App fee already exists  {email}')
                    app_exists += 1
                elif result in ('created', 'dry_created'):
                    app_created += 1

                # ── Renewal fee ──────────────────────────────────────────────
                if paid_renewal:
                    result = _ensure_payment(
                        user=user, application=application,
                        amount=RENEWAL_FEE,
                        description='Membership Renewal Fee',
                        payment_type='membership_renewal',
                        registered_by=admin,
                        note=note,
                        dry_run=dry_run,
                        stdout=self.stdout, style=self.style,
                    )
                    if result == 'exists':
                        self.stdout.write(f'  –  Renewal already exists  {email}')
                        renew_exists += 1
                    elif result in ('created', 'dry_created'):
                        renew_created += 1

            if dry_run:
                transaction.set_rollback(True)

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write(f'\n{"="*70}')
        self.stdout.write(self.style.SUCCESS('  SUMMARY'))
        self.stdout.write(f'{"="*70}')
        self.stdout.write(f'  Application fee records created : {app_created}')
        self.stdout.write(f'  Application fee already existed : {app_exists}')
        self.stdout.write(f'  Renewal fee records created     : {renew_created}')
        self.stdout.write(f'  Renewal fee already existed     : {renew_exists}')
        self.stdout.write(f'  Emails not in system            : {len(not_found)}')

        if not_found:
            self.stdout.write(f'\n  Not found ({len(not_found)}):')
            for e in not_found:
                self.stdout.write(f'    • {e}')

        total_revenue = (app_created * 50000) + (renew_created * 150000)
        self.stdout.write(
            f'\n  Revenue that will be added to stats: UGX {total_revenue:,}'
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  DRY RUN — no changes were written.'))
            self.stdout.write('  Remove --dry-run to apply.')
        else:
            self.stdout.write(self.style.SUCCESS('\n  ✓ Reconciliation complete.'))
