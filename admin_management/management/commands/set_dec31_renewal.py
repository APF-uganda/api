"""
One-time command: set subscription_due_date to December 31, 2026
for all existing members who joined before today.

New members (joined after today) keep whatever date they get
from get_annual_renewal_date() which now returns Dec 31 of their join year.

Usage:
  python manage.py set_dec31_renewal --dry-run
  python manage.py set_dec31_renewal
"""

from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()
TARGET_DATE = date(2026, 12, 31)


class Command(BaseCommand):
    help = 'Set subscription_due_date to 2026-12-31 for all existing members'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
            help='Preview — no changes made')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  ⚠️  DRY RUN — no changes will be made\n'))

        # All members who joined on or before today
        members = User.objects.filter(
            role='2',
            created_at__date__lte=today,
        )

        total   = members.count()
        updated = 0
        already = 0

        for m in members:
            if m.subscription_due_date == TARGET_DATE:
                already += 1
                continue
            if not dry_run:
                m.subscription_due_date = TARGET_DATE
                m.save(update_fields=['subscription_due_date'])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'\n{"="*55}'))
        self.stdout.write(self.style.SUCCESS(f'  SET RENEWAL DATE → {TARGET_DATE}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*55}'))
        self.stdout.write(f'  Total members     : {total}')
        self.stdout.write(self.style.SUCCESS(
            f'  {"Would update" if dry_run else "Updated"}  : {updated}'
        ))
        self.stdout.write(f'  Already correct   : {already}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n  DRY RUN — remove --dry-run to apply.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n  ✓ Done. All {updated} members now have renewal date {TARGET_DATE}.'
            ))
