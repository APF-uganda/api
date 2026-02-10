"""
Sync user/profile data from approved applications.
Usage: python manage.py sync_application_profiles
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from applications.models import Application
from Documents.models import Document
from profiles.models import UserProfile


class Command(BaseCommand):
    help = 'Sync approved application data into linked user/profile records.'

    def handle(self, *args, **options):
        applications = Application.objects.filter(status='approved', user__isnull=False).select_related('user')
        total_count = applications.count()

        if total_count == 0:
            self.stdout.write(self.style.WARNING('No approved applications with linked users found'))
            return

        self.stdout.write(f'Found {total_count} approved application(s) with linked users')

        updated_users = 0
        updated_profiles = 0
        skipped = 0
        errors = 0

        for application in applications:
            user = application.user
            if not user:
                skipped += 1
                continue

            try:
                with transaction.atomic():
                    user_updated = False
                    if not user.first_name and application.first_name:
                        user.first_name = application.first_name
                        user_updated = True
                    if not user.last_name and application.last_name:
                        user.last_name = application.last_name
                        user_updated = True
                    if not user.phone_number and application.phone_number:
                        user.phone_number = application.phone_number
                        user_updated = True
                    if not user.national_id_number and application.national_id_number:
                        user.national_id_number = application.national_id_number
                        user_updated = True
                    if not user.icpau_registration_number and application.icpau_certificate_number:
                        user.icpau_registration_number = application.icpau_certificate_number
                        user_updated = True

                    if user_updated:
                        user.save(update_fields=[
                            'first_name',
                            'last_name',
                            'phone_number',
                            'national_id_number',
                            'icpau_registration_number'
                        ])
                        updated_users += 1

                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile_updated = False
                    if not profile.first_name and application.first_name:
                        profile.first_name = application.first_name
                        profile_updated = True
                    if not profile.last_name and application.last_name:
                        profile.last_name = application.last_name
                        profile_updated = True
                    if not profile.phone_number and application.phone_number:
                        profile.phone_number = application.phone_number
                        profile_updated = True
                    if not profile.address_line_1 and application.address:
                        profile.address_line_1 = application.address
                        profile_updated = True
                    if not profile.icpau_registration_number and application.icpau_certificate_number:
                        profile.icpau_registration_number = application.icpau_certificate_number
                        profile_updated = True
                    if not profile.profile_picture:
                        passport_doc = Document.objects.filter(
                            application=application,
                            document_type='passport_photo'
                        ).first()
                        if not passport_doc:
                            passport_doc = Document.objects.filter(
                                application=application,
                                file_name__icontains='passport'
                            ).first()
                        if passport_doc and passport_doc.file and passport_doc.file.storage.exists(passport_doc.file.name):
                            profile.profile_picture = passport_doc.file
                            profile_updated = True

                    if profile_updated:
                        profile.save()
                        updated_profiles += 1

                    if not user_updated and not profile_updated:
                        skipped += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error syncing application {application.id} ({application.email}): {str(e)}'
                    )
                )
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSync completed:\n'
                f'  - Total applications checked: {total_count}\n'
                f'  - Users updated: {updated_users}\n'
                f'  - Profiles updated: {updated_profiles}\n'
                f'  - Skipped (no changes): {skipped}\n'
                f'  - Errors: {errors}'
            )
        )
