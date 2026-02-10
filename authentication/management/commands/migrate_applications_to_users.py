"""
Management command to migrate existing approved applications to user accounts.
Usage: python manage.py migrate_applications_to_users
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from applications.models import Application
from django.contrib.auth.hashers import identify_hasher, make_password
from authentication.models import User, UserRole
from profiles.models import UserProfile
from Documents.models import Document


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
                    
                    raw_or_hashed_password = application.password_hash
                    try:
                        identify_hasher(raw_or_hashed_password)
                        password_to_store = raw_or_hashed_password
                    except Exception:
                        password_to_store = make_password(raw_or_hashed_password)

                    # Create User record from Application
                    user = User.objects.create(
                        email=application.email,
                        password=password_to_store,
                        role=UserRole.MEMBER,  # Set role to 2 (member)
                        is_active=True,
                        first_name=application.first_name or '',
                        last_name=application.last_name or '',
                        phone_number=application.phone_number or '',
                        national_id_number=application.national_id_number or '',
                        icpau_registration_number=application.icpau_certificate_number or ''
                    )

                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.first_name = application.first_name or ''
                    profile.last_name = application.last_name or ''
                    profile.phone_number = application.phone_number or ''
                    profile.address_line_1 = application.address or ''
                    profile.icpau_registration_number = application.icpau_certificate_number or ''
                    passport_doc = Document.objects.filter(
                        application=application,
                        document_type='passport_photo'
                    ).first()
                    if not passport_doc:
                        passport_doc = Document.objects.filter(
                            application=application,
                            file_name__icontains='passport'
                        ).first()
                    if passport_doc and not profile.profile_picture:
                        if passport_doc.file and passport_doc.file.storage.exists(passport_doc.file.name):
                            profile.profile_picture = passport_doc.file
                    profile.save()

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
