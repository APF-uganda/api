"""
Management command to reconcile payments from the official APF members register.

This command sets payment statuses for members listed in the register as having paid.
Members not found in the system are skipped and reported.

Usage:
  # Preview what would change — no DB writes
  python manage.py reconcile_payments --dry-run

  # Apply the changes
  python manage.py reconcile_payments
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

User = get_user_model()

# ── Official members register as at 4th February 2026 ────────────────────────
# Format: (email, paid_application_fee, paid_renewal_fee)
# Amounts in UGX
MEMBERS_REGISTER = [
    ("kherman32@gmail.com",               50000,  0),
    ("patrickmugarura10@yahoo.com",        50000,  0),
    ("gkkakala@gmail.com",                 50000,  50000),   # renewal listed as 50k in source
    ("constant.mayende@gmail.com",         50000,  150000),
    ("r.albert.otete@gmail.com",           50000,  0),
    ("maria@springstugye.com",             50000,  0),
    ("nuwamanyageoffrey@gmail.com",        50000,  0),
    ("rmutumba@mutumbamukobe.org",         50000,  0),
    ("emojongodeke@gmail.com",             50000,  0),
    # Two emails for David Nyende — try both
    ("mante@continentalpartners.org",      50000,  150000),
    ("gard662@gmail.com",                  50000,  150000),
    ("justin@osillocpa.com",               50000,  0),
    ("senogaassociates@gmail.com",         50000,  0),
    ("michael@springstugye.com",           50000,  0),
    ("a.arnold@ardenfield.com",            50000,  0),
    ("a.dennis@ardenfield.com",            50000,  0),
    ("pius.ssuuna@gmail.com",              50000,  0),
    ("rhodaochan@gmail.com",               50000,  0),
    ("annetnantumbwe1@gmail.com",          50000,  0),
    ("ochanbernard@gmail.com",             50000,  0),
    ("sekiziyivuissa@gmail.com",           50000,  0),
    ("msilverboss@gmail.com",              50000,  0),
    ("muke280@gmail.com",                  50000,  0),
    ("lmawanda45@gmail.com",               50000,  0),
    ("kalindaassociates@gmail.com",        50000,  0),
    ("chrisnet4@gmail.com",                50000,  0),
    ("info@pepartnersuganda.com",          50000,  150000),
    ("jay.oriekot@gmail.com",              50000,  0),
    ("rwomus.stepehn@gmail.com",           50000,  0),
    ("annerozbob1@gmail.com",              50000,  0),
    ("abdul@springstugye.com",             50000,  0),
    ("pkbanadda@gmail.com",                50000,  0),
    ("woodhask.ediomu@woodhask.com",       50000,  0),
    ("biz.bizandcompany@gmail.com",        50000,  150000),
    ("glutwama@gmail.com",                 50000,  0),
    ("dssebugwawo@gmail.com",              50000,  0),
    ("arch.archelia@gmail.com",            50000,  0),
    ("kabuchualfred@gmail.com",            50000,  0),
    ("jbmwanja@gmail.com",                 50000,  0),
    ("gadzk@yahoo.com",                    50000,  0),
    ("otimotile@yahoo.com",                50000,  0),
    ("rmatsiko89@gmail.com",               50000,  0),
    ("davidssenoga@gmail.com",             50000,  150000),  # fixed typo: gmail,com → gmail.com
    ("bwireb@gmail.com",                   50000,  0),
    ("thomsonkwizina@gmail.com",           50000,  0),
    ("mwagodassociates@gmail.com",         50000,  0),
    ("jamiekasule@yahoo.com",              50000,  0),
    ("peterkasango1@gmail.com",            50000,  150000),
    ("marknsubugacpa@gmail.com",           50000,  0),
    ("rwebishugi@gmail.com",               50000,  0),
    ("basiima55@yahoo.co.uk",              50000,  0),
    ("fmtwine@gmail.com",                  50000,  0),
    ("kasawulibaker@gmail.com",            50000,  150000),
    ("rkyalimpa@gmail.com",                50000,  0),
    ("manyiredith@gmail.com",              50000,  150000),
    ("sgabula2001@yahoo.co.uk",            50000,  0),
    # Rows 55,57-60 have no email — skipped
]


class Command(BaseCommand):
    help = 'Reconcile payment statuses from the official APF members register (Feb 2026)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without writing to the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        from payments.models import ManualPayment
        from applications.models import Application
        from decimal import Decimal

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  ⚠️  DRY RUN — no changes will be made\n'))

        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS('  RECONCILE PAYMENTS — APF Members Register Feb 2026'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))

        not_found = []
        app_fee_verified = 0
        app_fee_skipped  = 0
        renewal_verified = 0
        renewal_created  = 0
        renewal_skipped  = 0

        with transaction.atomic():
            for email, app_fee, renewal_fee in MEMBERS_REGISTER:
                email = email.lower().strip()
                user = User.objects.filter(email__iexact=email).first()

                if not user:
                    not_found.append(email)
                    self.stdout.write(self.style.WARNING(f'  ⚠  NOT FOUND   {email}'))
                    continue

                # ── Application fee payment ──────────────────────────────────
                app_payment = (
                    ManualPayment.objects
                    .filter(user=user, payment_type='membership_renewal')
                    .order_by('-created_at')
                    .first()
                )
                if not app_payment:
                    # Try via application FK
                    app_obj = Application.objects.filter(email__iexact=email).first()
                    if app_obj:
                        app_payment = (
                            ManualPayment.objects
                            .filter(application=app_obj)
                            .order_by('-created_at')
                            .first()
                        )

                if app_payment:
                    if app_payment.status != ManualPayment.STATUS_VERIFIED:
                        if not dry_run:
                            app_payment.status = ManualPayment.STATUS_VERIFIED
                            app_payment.verified_at = app_payment.verified_at or timezone.now()
                            app_payment.verification_notes = 'Verified via official register reconciliation (Feb 2026)'
                            app_payment.save(update_fields=['status', 'verified_at', 'verification_notes'])
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓  APP FEE verified    {email}'
                        ))
                        app_fee_verified += 1
                    else:
                        self.stdout.write(f'  –  APP FEE already OK  {email}')
                        app_fee_skipped += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠  APP FEE no record  {email}  (no ManualPayment found)'
                    ))
                    app_fee_skipped += 1

                # ── Renewal fee payment ──────────────────────────────────────
                if renewal_fee > 0:
                    renewal_payment = (
                        ManualPayment.objects
                        .filter(
                            user=user,
                            payment_type='membership_renewal',
                            amount__gte=Decimal('100000'),   # renewal is 150k, not app fee 50k
                        )
                        .order_by('-created_at')
                        .first()
                    )

                    if renewal_payment:
                        if renewal_payment.status != ManualPayment.STATUS_VERIFIED:
                            if not dry_run:
                                renewal_payment.status = ManualPayment.STATUS_VERIFIED
                                renewal_payment.verified_at = renewal_payment.verified_at or timezone.now()
                                renewal_payment.verification_notes = 'Verified via official register reconciliation (Feb 2026)'
                                renewal_payment.save(update_fields=['status', 'verified_at', 'verification_notes'])
                            self.stdout.write(self.style.SUCCESS(
                                f'  ✓  RENEWAL verified   {email}'
                            ))
                            renewal_verified += 1
                        else:
                            self.stdout.write(f'  –  RENEWAL already OK  {email}')
                            renewal_skipped += 1
                    else:
                        # No renewal payment exists — create one as already verified
                        app_obj = Application.objects.filter(
                            user=user
                        ).order_by('-submitted_at').first()
                        if app_obj and not dry_run:
                            ManualPayment.objects.create(
                                application=app_obj,
                                user=user,
                                amount=Decimal(str(renewal_fee)),
                                currency='UGX',
                                reference=f'REGISTER-RENEWAL-{email}',
                                description='Membership Renewal Fee',
                                payment_type='membership_renewal',
                                status=ManualPayment.STATUS_VERIFIED,
                                verified_at=timezone.now(),
                                verification_notes='Back-filled from official register reconciliation (Feb 2026)',
                                proof_of_payment='',  # No receipt — admin reconciliation
                            )
                            self.stdout.write(self.style.SUCCESS(
                                f'  ✓  RENEWAL created    {email}  (UGX {renewal_fee:,})'
                            ))
                            renewal_created += 1
                        elif dry_run:
                            self.stdout.write(self.style.SUCCESS(
                                f'  [DRY] Would create RENEWAL for {email}  (UGX {renewal_fee:,})'
                            ))
                            renewal_created += 1
                        else:
                            self.stdout.write(self.style.WARNING(
                                f'  ⚠  RENEWAL skipped   {email}  (no linked application to attach to)'
                            ))
                            renewal_skipped += 1

            if dry_run:
                # Roll back all changes in dry-run
                transaction.set_rollback(True)

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write(f'\n{"="*70}')
        self.stdout.write(self.style.SUCCESS('  SUMMARY'))
        self.stdout.write(f'{"="*70}')
        self.stdout.write(f'  Application fee verified:  {app_fee_verified}')
        self.stdout.write(f'  Application fee skipped:   {app_fee_skipped}  (already OK or no record)')
        self.stdout.write(f'  Renewal fee verified:      {renewal_verified}')
        self.stdout.write(f'  Renewal fee created:       {renewal_created}  (back-filled)')
        self.stdout.write(f'  Renewal fee skipped:       {renewal_skipped}')
        self.stdout.write(f'  Emails not in system:      {len(not_found)}')

        if not_found:
            self.stdout.write(f'\n  Not found in system ({len(not_found)}):')
            for e in not_found:
                self.stdout.write(f'    • {e}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  DRY RUN — no changes were written.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n  ✓ Reconciliation complete.'))
            self.stdout.write('  Run the stats endpoint to verify updated revenue totals.')
