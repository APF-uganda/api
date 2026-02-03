"""
Deactivate users who only have rejected applications.
Usage: python manage.py deactivate_rejected_application_users
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from applications.models import Application
from authentication.models import User


class Command(BaseCommand):
    help = 'Deactivate users whose applications are all rejected (no approved/pending).'

    def handle(self, *args, **options):
        emails = Application.objects.filter(status='rejected').values_list('email', flat=True).distinct()

        deactivated = 0
        skipped = 0
        errors = 0

        for email in emails:
            if not email:
                continue

            try:
                with transaction.atomic():
                    has_non_rejected = Application.objects.filter(email__iexact=email).exclude(status='rejected').exists()
                    if has_non_rejected:
                        skipped += 1
                        continue

                    user = User.objects.filter(email__iexact=email, is_active=True).first()
                    if not user:
                        skipped += 1
                        continue

                    user.is_active = False
                    user.save(update_fields=['is_active'])
                    deactivated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error deactivating {email}: {str(e)}'))
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDeactivation completed:\n'
                f'  - Deactivated: {deactivated}\n'
                f'  - Skipped: {skipped}\n'
                f'  - Errors: {errors}'
            )
        )
