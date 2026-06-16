"""
Management command to reconcile payments from the official APF members register.

Creates verified ManualPayment records for:
  - Application fee (UGX 50,000) — reference = member's application ID (APF-YYYY-NNNNNN)
  - Renewal fee (UGX 150,000)   — reference = INV-YYYY-USERID-TIMESTAMP format

Members not found in the system are skipped and reported.
Existing verified records are never duplicated.

Usage:
  python manage.py reconcile_payments --dry-run    # preview, no changes
  python manage.py reconcile_payments              # apply
  python manage.py reconcile_payments --undo       # delete all records created by this script
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import datetime

User = get_user_model()

APP_FEE     = Decimal('50000.00')
RENEWAL_FEE = Decimal('150000.00')
RECONCILE_NOTE = 'Back-filled from official APF members register (Feb 2026) via reconcile_payments'

# ── Official members register as at 4th February 2026 ────────────────────────
# (email, paid_renewal)
MEMBERS_REGISTER = [
    ("kherman32@gmail.com",             False),
    ("patrickmugarura10@yahoo.com",     False),
    ("gkkakala@gmail.com",              False),
    ("constant.mayende@gmail.com",      True),
    ("r.albert.otete@gmail.com",        False),
    ("maria@springstugye.com",          False),
    ("nuwamanyageoffrey@gmail.com",     False),
    ("rmutumba@mutumbamukobe.org",      False),
    ("emojongodeke@gmail.com",          False),
    ("mante@continentalpartners.org",   True),
    ("gard662@gmail.com",               True),
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
    ("davidssenoga@gmail.com",          True),
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
]


def _generate_invoice_number(user_id):
    """Match the format used by MembershipRenewalService.generate_invoice_number()"""
    year = datetime.now().year
    timestamp = datetime.now().strftime('%m%d%H%M%S')
    return f"INV-{year}-{user_id}-{timestamp}"


class Command(BaseCommand):
    help = 'Reconcile payment records from the official APF members register (Feb 2026)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
            help='Preview changes without writing to the database')
        parser.add_argument('--undo', action='store_true',
            help='Delete all payment records created by this script (identified by note)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        undo    = options['undo']

        if undo:
            self._undo()
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  ⚠️  DRY RUN — no changes will be made\n'))

        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS('  RECONCILE PAYMENTS — APF Members Register Feb 2026'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))

        admin = User.objects.filter(role='1').order_by('id').first()

        not_found     = []
        app_created   = app_exists   = 0
        renew_created = renew_exists = 0

        with transaction.atomic():
            for email, paid_renewal in MEMBERS_REGISTER:
                email = email.lower().strip()
                user = User.objects.filter(email__iexact=email).first()

                if not user:
                    not_found.append(email)
                    self.stdout.write(self.style.WARNING(f'  ⚠  NOT FOUND  {email}'))
                    continue

                application = self._get_or_create_stub_application(user)

                # ── Application fee ──────────────────────────────────────────
                # Reference = the member's application ID e.g. APF-2026-000042
                app_reference = (
                    application.application_id
                    if application
                    else f"APF-MANUAL-{user.id}"
                )
                r = self._ensure_payment(
                    user=user, application=application,
                    amount=APP_FEE,
                    reference=app_reference,
                    description='Application Fee',
                    dry_run=dry_run,
                )
                if r == 'exists':
                    self.stdout.write(f'  –  App fee exists       {email}  ({app_reference})')
                    app_exists += 1
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓  App fee {"(DRY)" if dry_run else "created"}   {email}  ref={app_reference}'
                    ))
                    app_created += 1

                # ── Renewal fee ──────────────────────────────────────────────
                # Reference = INV-YYYY-USERID-TIMESTAMP (matches invoice number format)
                if paid_renewal:
                    inv_reference = _generate_invoice_number(user.id)
                    r = self._ensure_payment(
                        user=user, application=application,
                        amount=RENEWAL_FEE,
                        reference=inv_reference,
                        description='Membership Renewal Fee',
                        dry_run=dry_run,
                        invoice_number=inv_reference,
                    )
                    if r == 'exists':
                        self.stdout.write(f'  –  Renewal exists       {email}')
                        renew_exists += 1
                    else:
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓  Renewal {"(DRY)" if dry_run else "created"}   {email}  ref={inv_reference}'
                        ))
                        renew_created += 1

            if dry_run:
                transaction.set_rollback(True)

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write(f'\n{"="*70}')
        self.stdout.write(f'  Application fee created : {app_created}  |  already existed: {app_exists}')
        self.stdout.write(f'  Renewal fee created     : {renew_created}  |  already existed: {renew_exists}')
        self.stdout.write(f'  Not in system           : {len(not_found)}')
        if not_found:
            for e in not_found:
                self.stdout.write(f'    • {e}')
        revenue = (app_created * 50000) + (renew_created * 150000)
        self.stdout.write(f'  Revenue added           : UGX {revenue:,}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  DRY RUN — nothing written. Remove --dry-run to apply.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n  ✓ Done.'))

    def _get_or_create_stub_application(self, user):
        from applications.models import Application
        app = Application.objects.filter(
            email__iexact=user.email
        ).order_by('-submitted_at').first()
        if app:
            return app
        # Create minimal stub so ManualPayment FK is satisfied
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

    def _ensure_payment(self, user, application, amount, reference,
                        description, dry_run, invoice_number=None):
        from payments.models import ManualPayment
        admin = User.objects.filter(role='1').order_by('id').first()

        # Check if an identical verified record already exists
        existing = ManualPayment.objects.filter(
            user=user,
            amount=amount,
            status=ManualPayment.STATUS_VERIFIED,
            verification_notes=RECONCILE_NOTE,
        ).first()
        if existing:
            return 'exists'

        if dry_run:
            return 'dry_created'

        ManualPayment.objects.create(
            application=application,
            user=user,
            amount=amount,
            currency='UGX',
            reference=reference,
            description=description,
            payment_type='membership_renewal',
            invoice_number=invoice_number or '',
            application_reference=application.application_id if application else '',
            status=ManualPayment.STATUS_VERIFIED,
            verified_by=admin,
            verified_at=timezone.now(),
            verification_notes=RECONCILE_NOTE,
            proof_of_payment='',
        )
        return 'created'

    def _undo(self):
        """Delete all payment records created by this script."""
        from payments.models import ManualPayment
        qs = ManualPayment.objects.filter(verification_notes=RECONCILE_NOTE)
        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No reconcile records found. Nothing to undo.'))
            return
        self.stdout.write(self.style.WARNING(f'Deleting {count} reconcile payment records...'))
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} records. Undo complete.'))
