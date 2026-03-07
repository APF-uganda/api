"""
Management command to migrate all existing members to April 1st renewal date
Run once to update all members to the new April 1st renewal system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def get_next_april_first():
    """
    Calculate the next April 1st renewal date.
    
    Returns:
        date: The next April 1st (current year if before April 1st, next year if after)
    """
    today = timezone.now().date()
    current_year = today.year
    
    # April 1st of current year
    april_first_this_year = date(current_year, 4, 1)
    
    # If today is before April 1st this year, return April 1st this year
    # Otherwise, return April 1st next year
    if today < april_first_this_year:
        return april_first_this_year
    else:
        return date(current_year + 1, 4, 1)


class Command(BaseCommand):
    help = 'Migrate all members to April 1st renewal date system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes (preview mode)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('Migrating all members to April 1st renewal system'))
        self.stdout.write('=' * 70)
        
        # Get all members (role='2')
        members = User.objects.filter(role='2')
        count = members.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No members found'))
            return
        
        self.stdout.write(f'Found {count} member(s) to migrate')
        self.stdout.write('')
        
        # Calculate the new renewal date
        new_renewal_date = get_next_april_first()
        self.stdout.write(
            self.style.SUCCESS(f'New renewal date for all members: {new_renewal_date}')
        )
        self.stdout.write('')
        
        updated_count = 0
        error_count = 0
        
        for member in members:
            try:
                old_date = member.subscription_due_date
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[DRY RUN] {member.email}: '
                            f'{old_date or "Not set"} → {new_renewal_date}'
                        )
                    )
                    updated_count += 1
                else:
                    member.subscription_due_date = new_renewal_date
                    member.save(update_fields=['subscription_due_date'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {member.email}: '
                            f'{old_date or "Not set"} → {new_renewal_date}'
                        )
                    )
                    
                    updated_count += 1
                    logger.info(
                        f'Migrated {member.email} to April 1st renewal: {new_renewal_date}'
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to update {member.email}: {str(e)}')
                )
                error_count += 1
                logger.error(f'Failed to migrate {member.email}: {e}')
        
        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('Migration Summary'))
        self.stdout.write('=' * 70)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes made'))
        
        self.stdout.write(f'Total members: {count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {updated_count}'))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if not dry_run and error_count == 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ All members migrated to April 1st renewal system!'
                )
            )
            self.stdout.write('')
            self.stdout.write('All members will now renew on April 1st each year.')
