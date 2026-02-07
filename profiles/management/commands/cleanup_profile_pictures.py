"""
Management command to clean up broken profile picture references.
Usage: python manage.py cleanup_profile_pictures
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from profiles.models import UserProfile
import os


class Command(BaseCommand):
    help = 'Clean up profile picture references that point to non-existent files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Profile Picture Cleanup'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\nDRY RUN MODE - No changes will be made\n'))
        
        # Get all profiles with profile pictures
        profiles_with_pictures = UserProfile.objects.exclude(profile_picture='').exclude(profile_picture=None)
        total_profiles = profiles_with_pictures.count()
        
        self.stdout.write(f'\nFound {total_profiles} profiles with profile pictures\n')
        
        broken_count = 0
        fixed_count = 0
        
        for profile in profiles_with_pictures:
            try:
                # Check if file exists
                if profile.profile_picture:
                    file_path = profile.profile_picture.path
                    
                    if not os.path.exists(file_path):
                        broken_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'✗ {profile.user.email}: File not found - {file_path}'
                            )
                        )
                        
                        if not dry_run:
                            # Clear the broken reference
                            profile.profile_picture = None
                            profile.save()
                            fixed_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  → Cleared broken reference'
                                )
                            )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ {profile.user.email}: File exists'
                            )
                        )
            except (ValueError, AttributeError, FileNotFoundError) as e:
                broken_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ {profile.user.email}: Error accessing file - {e}'
                    )
                )
                
                if not dry_run:
                    # Clear the broken reference
                    profile.profile_picture = None
                    profile.save()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  → Cleared broken reference'
                        )
                    )
        
        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.WARNING('SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'\nTotal profiles checked: {total_profiles}')
        self.stdout.write(f'Broken references found: {broken_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f'\nDRY RUN: Would fix {broken_count} broken references'
                )
            )
            self.stdout.write(
                self.style.NOTICE(
                    '\nRun without --dry-run to apply changes'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nFixed: {fixed_count} broken references'
                )
            )
        
        self.stdout.write('\n')
