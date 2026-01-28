"""
Management command to migrate existing approved applications to user accounts.
Usage: python manage.py migrate_applications_to_users
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from applications.models import Application
from authentication.models import User, UserRole


class Command(BaseCommand):
    help = 'Migrate approved applications without linked User accounts to User records'

    def handle(self, *args, **options):
        # Find all approved Applications without linked User accounts
        approved_applications = Application.objects.filter(
            status='approved',
            user__isnull=True
        )
        
        total_count = approved_applications.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No approved applications found without linked user accounts')
            )
            return
        
        self.stdout.write(f'Found {total_count} approved application(s) to migrate')
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for application in approved_applications:
            try:
                with transaction.atomic():
                    # Check if User already exists for this email
                    if User.objects.filter(email=application.email).exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f'Skipped: User already exists for email {application.email}'
                            )
                        )
                        skipped_count += 1
                        continue
                    
                    # Create User record from Application
                    user = User.objects.create(
                        email=application.email,
                        password=application.password_hash,  # Already hashed
                        role=UserRole.MEMBER,  # Set role to 2 (member)
                        is_active=True
                    )
                    
                    # Link User to Application
                    application.user = user
                    application.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created user for {application.email} (User ID: {user.id}, Application ID: {application.id})'
                        )
                    )
                    success_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error migrating application {application.id} ({application.email}): {str(e)}'
                    )
                )
                error_count += 1
        
        # Log migration statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'\nMigration completed:\n'
                f'  - Total applications found: {total_count}\n'
                f'  - Successfully migrated: {success_count}\n'
                f'  - Skipped (user exists): {skipped_count}\n'
                f'  - Errors: {error_count}'
            )
        )
