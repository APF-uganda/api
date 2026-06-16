"""
Management command to delete ALL ManualPayment records EXCEPT those
belonging to members listed in the official APF register (Feb 2026).

Usage:
  python manage.py clean_payments --dry-run   # preview — no changes
  python manage.py clean_payments             # delete
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

# Emails to KEEP — from the official register
KEEP_EMAILS = {
    "kherman32@gmail.com",
    "patrickmugarura10@yahoo.com",
    "gkkakala@gmail.com",
    "constant.mayende@gmail.com",
    "r.albert.otete@gmail.com",
    "maria@springstugye.com",
    "nuwamanyageoffrey@gmail.com",
    "rmutumba@mutumbamukobe.org",
    "emojongodeke@gmail.com",
    "mante@continentalpartners.org",
    "gard662@gmail.com",
    "justin@osillocpa.com",
    "senogaassociates@gmail.com",
    "michael@springstugye.com",
    "a.arnold@ardenfield.com",
    "a.dennis@ardenfield.com",
    "pius.ssuuna@gmail.com",
    "rhodaochan@gmail.com",
    "annetnantumbwe1@gmail.com",
    "ochanbernard@gmail.com",
    "sekiziyivuissa@gmail.com",
    "msilverboss@gmail.com",
    "muke280@gmail.com",
    "lmawanda45@gmail.com",
    "kalindaassociates@gmail.com",
    "chrisnet4@gmail.com",
    "info@pepartnersuganda.com",
    "jay.oriekot@gmail.com",
    "rwomus.stepehn@gmail.com",
    "annerozbob1@gmail.com",
    "abdul@springstugye.com",
    "pkbanadda@gmail.com",
    "woodhask.ediomu@woodhask.com",
    "biz.bizandcompany@gmail.com",
    "glutwama@gmail.com",
    "dssebugwawo@gmail.com",
    "arch.archelia@gmail.com",
    "kabuchualfred@gmail.com",
    "jbmwanja@gmail.com",
    "gadzk@yahoo.com",
    "otimotile@yahoo.com",
    "rmatsiko89@gmail.com",
    "davidssenoga@gmail.com",
    "bwireb@gmail.com",
    "thomsonkwizina@gmail.com",
    "mwagodassociates@gmail.com",
    "jamiekasule@yahoo.com",
    "peterkasango1@gmail.com",
    "marknsubugacpa@gmail.com",
    "rwebishugi@gmail.com",
    "basiima55@yahoo.co.uk",
    "fmtwine@gmail.com",
    "kasawulibaker@gmail.com",
    "rkyalimpa@gmail.com",
    "manyiredith@gmail.com",
    "sgabula2001@yahoo.co.uk",
}


class Command(BaseCommand):
    help = 'Delete all ManualPayment records except those belonging to official register members'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
            help='Preview what will be deleted — no changes made')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        from payments.models import ManualPayment

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  ⚠️  DRY RUN — no changes will be made\n'))

        self.stdout.write(self.style.SUCCESS(f'\n{"="*65}'))
        self.stdout.write(self.style.SUCCESS('  CLEAN PAYMENTS — keep only official register members'))
        self.stdout.write(self.style.SUCCESS(f'{"="*65}\n'))

        # Find user IDs for the emails we want to keep
        keep_user_ids = set(
            User.objects.filter(email__in=KEEP_EMAILS).values_list('id', flat=True)
        )
        self.stdout.write(f'  Register emails found in system : {len(keep_user_ids)}')
        self.stdout.write(f'  Register emails not in system   : {len(KEEP_EMAILS) - len(keep_user_ids)}')

        # All payments — split into keep and delete
        total = ManualPayment.objects.count()

        # Keep: payments linked to register users (by user FK or by application email)
        from applications.models import Application
        keep_app_ids = set(
            Application.objects.filter(
                email__in=KEEP_EMAILS
            ).values_list('id', flat=True)
        )

        to_delete = ManualPayment.objects.exclude(
            user_id__in=keep_user_ids
        ).exclude(
            application_id__in=keep_app_ids
        )

        delete_count = to_delete.count()
        keep_count   = total - delete_count

        self.stdout.write(f'  Total ManualPayment records     : {total}')
        self.stdout.write(f'  Records to KEEP                 : {keep_count}')
        self.stdout.write(self.style.ERROR(f'  Records to DELETE               : {delete_count}'))

        if delete_count == 0:
            self.stdout.write(self.style.SUCCESS('\nNothing to delete.'))
            return

        # Show what will be deleted
        self.stdout.write(f'\n  {"ID":<6}  {"Member":<40}  {"Amount":>12}  {"Status"}')
        self.stdout.write('  ' + '-'*70)
        for p in to_delete.select_related('user', 'application').order_by('id'):
            member = (
                p.user.email if p.user
                else (p.application.email if p.application else 'unknown')
            )
            self.stdout.write(
                f'  {p.id:<6}  {member:<40}  '
                f'UGX {int(p.amount):>8,}  {p.status}'
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n  DRY RUN — {delete_count} record(s) would be deleted. '
                'Remove --dry-run to apply.'
            ))
            return

        # Confirm
        self.stdout.write(self.style.ERROR(
            f'\n  ⚠️  About to permanently delete {delete_count} payment record(s).'
        ))
        confirm = input('  Type "DELETE" to confirm: ').strip()
        if confirm != 'DELETE':
            self.stdout.write(self.style.WARNING('Aborted — no changes made.'))
            return

        with transaction.atomic():
            deleted, _ = to_delete.delete()

        self.stdout.write(self.style.SUCCESS(f'\n  ✓ Deleted {deleted} payment records.'))
        self.stdout.write(f'  Remaining ManualPayment records: {ManualPayment.objects.count()}')
