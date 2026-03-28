"""
Management command to fix renewal dates for all members
Sets all renewal dates to March 31st (current or next year)
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date

User = get_user_model()


def get_march_31_renewal_date(base_date=None):
    """
    Calculate renewal date - always March 31st.
    If base date is after March 31st, renewal is March 31st of next year.
    Otherwise, renewal is March 31st of current year.
    """
    if base_date is None:
        base_date = timezone.now().date()
    elif hasattr(base_date, 'date'):
        base_date = base_date.date()

    # Renewal date is always March 31st
    renewal_month = 3
    renewal_day = 31
    
    # Determine the year for renewal
    current_year = base_date.year
    renewal_date_this_year = base_date.replace(month=renewal_month, day=renewal_day, year=current_year)
    
    # If the base date is after March 31st of the current year, 
    # set renewal to March 31st of next year
    if base_date > renewal_date_this_year:
        return base_date.replace(month=renewal_month, day=renewal_day, year=current_year + 1)
    else:
        # Otherwise, renewal is March 31st of the current year
        return renewal_date_this_year


class Command(BaseCommand):
    help = 'Fix renewal dates for all members - set to March 31st'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('FIX MEMBER RENEWAL DATES TO MARCH 31ST'))
        self.stdout.write('=' * 70)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Get all members (role='2')
        members = User.objects.filter(role='2')
        total_members = members.count()
        
        self.stdout.write(f'\n📊 Found {total_members} members\n')
        
        if total_members == 0:
            self.stdout.write(self.style.WARNING('No members found.'))
            return
        
        updated_count = 0
        skipped_count = 0
        
        today = timezone.now().date()
        
        for member in members:
            # Use created_at as base date if subscription_due_date is not set
            base_date = member.subscription_due_date or member.created_at.date()
            
            # Calculate the correct March 31st renewal date
            correct_renewal_date = get_march_31_renewal_date(base_date)
            
            # Check if update is needed
            if member.subscription_due_date != correct_renewal_date:
                old_date = member.subscription_due_date or 'Not Set'
                
                if dry_run:
                    self.stdout.write(
                        f'  Would update: {member.email}\n'
                        f'    Old: {old_date}\n'
                        f'    New: {correct_renewal_date}\n'
                    )
                else:
                    member.subscription_due_date = correct_renewal_date
                    member.save(update_fields=['subscription_due_date'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Updated: {member.email}\n'
                            f'    Old: {old_date}\n'
                            f'    New: {correct_renewal_date}\n'
                        )
                    )
                
                updated_count += 1
            else:
                skipped_count += 1
        
        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total members: {total_members}')
        
        if dry_run:
            self.stdout.write(f'Would update: {updated_count}')
            self.stdout.write(f'Already correct: {skipped_count}')
            self.stdout.write('\n' + self.style.WARNING('Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))
            self.stdout.write(f'Already correct: {skipped_count}')
            self.stdout.write('\n' + self.style.SUCCESS('✅ All renewal dates fixed!'))
        
        self.stdout.write('=' * 70 + '\n')
