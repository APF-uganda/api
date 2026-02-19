"""
Management command to set initial subscription dates for existing members
Run once to populate subscription_due_date for members who don't have it set
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set initial subscription due dates for existing members based on their join date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes (preview mode)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update all members, even those with existing subscription dates',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('Setting initial subscription dates for members'))
        self.stdout.write('=' * 60)
        
        # Find members without subscription_due_date (or all if force)
        if force:
            members = User.objects.filter(role='2')
            self.stdout.write(self.style.WARNING('FORCE mode: Updating ALL members'))
        else:
            members = User.objects.filter(
                role='2',
                subscription_due_date__isnull=True
            )
        
        count = members.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No members need subscription dates set'))
            return
        
        self.stdout.write(f'Found {count} member(s) to update')
        self.stdout.write('')
        
        updated_count = 0
        error_count = 0
        
        for member in members:
            try:
                # Calculate subscription due date: 1 year from when they joined
                join_date = member.created_at.date()
                new_due_date = join_date + timedelta(days=365)
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[DRY RUN] Would set {member.email}: '
                            f'joined {join_date} → due date {new_due_date}'
                        )
                    )
                    updated_count += 1
                else:
                    old_date = member.subscription_due_date
                    member.subscription_due_date = new_due_date
                    member.save(update_fields=['subscription_due_date'])
                    
                    if old_date:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated {member.email}: '
                                f'{old_date} → {new_due_date} (joined {join_date})'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Set {member.email}: '
                                f'due date {new_due_date} (joined {join_date})'
                            )
                        )
                    
                    updated_count += 1
                    logger.info(f'Set subscription due date for {member.email} to {new_due_date}')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to update {member.email}: {str(e)}'
                    )
                )
                error_count += 1
                logger.error(f'Failed to set subscription date for {member.email}: {e}')
        
        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write('=' * 60)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes made'))
        
        self.stdout.write(f'Total members processed: {count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully updated: {updated_count}'))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if not dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ Subscription dates have been set!'))
            self.stdout.write('')
            self.stdout.write('Next steps:')
            self.stdout.write('1. Verify the dates in the admin panel')
            self.stdout.write('2. Run: python manage.py check_expired_subscriptions --dry-run')
            self.stdout.write('3. Set up daily cron job for automatic expiration checks')
