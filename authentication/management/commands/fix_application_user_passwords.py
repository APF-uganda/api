"""
Fix user passwords for accounts created from applications.
Ensures users linked to approved applications have properly hashed passwords.
Usage: python manage.py fix_application_user_passwords
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.hashers import identify_hasher, make_password
from applications.models import Application


class Command(BaseCommand):
    help = 'Fix passwords for users linked to approved applications if stored unhashed.'

    def handle(self, *args, **options):
        applications = Application.objects.filter(status='approved', user__isnull=False).select_related('user')
        total_count = applications.count()

        if total_count == 0:
            self.stdout.write(self.style.WARNING('No approved applications with linked users found'))
            return

        self.stdout.write(f'Found {total_count} approved application(s) with linked users')

        fixed_count = 0
        skipped_count = 0
        error_count = 0

        for application in applications:
            user = application.user
            if not user:
                continue

            try:
                with transaction.atomic():
                    try:
                        identify_hasher(user.password)
                        skipped_count += 1
                        continue
                    except Exception:
                        pass

                    raw_or_hashed_password = application.password_hash
                    try:
                        identify_hasher(raw_or_hashed_password)
                        user.password = raw_or_hashed_password
                    except Exception:
                        user.password = make_password(raw_or_hashed_password)

                    user.save(update_fields=['password'])
                    fixed_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error fixing password for user {user.email} (Application ID: {application.id}): {str(e)}'
                    )
                )
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPassword fix completed:\n'
                f'  - Total applications checked: {total_count}\n'
                f'  - Passwords fixed: {fixed_count}\n'
                f'  - Skipped (already hashed): {skipped_count}\n'
                f'  - Errors: {error_count}'
            )
        )
