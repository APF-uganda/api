"""
Management command to check for expired subscriptions and suspend users
Run this command daily via cron job or task scheduler

DISABLED: Automatic suspension has been disabled per admin request.
Admins now manually suspend members using the admin dashboard.
This command is kept for reference but will not suspend users automatically.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from admin_management.services import MemberManagementService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check for expired subscriptions (AUTOMATIC SUSPENSION DISABLED - REPORT ONLY)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes (preview mode)',
        )

    def handle(self, *args, **options):
        # AUTOMATIC SUSPENSION DISABLED
        # This command now only reports expired subscriptions
        # Admins must manually suspend members via the admin dashboard
        
        today = timezone.now().date()
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('AUTOMATIC SUSPENSION IS DISABLED'))
        self.stdout.write(self.style.WARNING('This command only reports expired subscriptions'))
        self.stdout.write(self.style.WARNING('Admins must manually suspend members via the dashboard'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS(f'Checking for expired subscriptions as of {today}'))
        
        # Find all members with expired subscriptions who are still active
        expired_members = User.objects.filter(
            role='2',  # Members only
            is_active=True,
            subscription_due_date__lt=today
        )
        
        count = expired_members.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired subscriptions found'))
            return
        
        self.stdout.write(self.style.WARNING(f'Found {count} member(s) with expired subscriptions'))
        self.stdout.write('')
        
        # REPORT ONLY - NO AUTOMATIC SUSPENSION
        for member in expired_members:
            days_overdue = (today - member.subscription_due_date).days
            self.stdout.write(
                self.style.WARNING(
                    f'⚠ {member.email} - expired {days_overdue} days ago on {member.subscription_due_date}'
                )
            )
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('--- Summary ---'))
        self.stdout.write(self.style.WARNING(f'Total expired: {count}'))
        self.stdout.write(self.style.WARNING('NO AUTOMATIC SUSPENSIONS PERFORMED'))
        self.stdout.write(self.style.WARNING('Admins must manually suspend members via the dashboard'))
        
        logger.info(f'Expired subscription check: {count} members with expired subscriptions (no auto-suspension)')
        
        # ORIGINAL AUTOMATIC SUSPENSION CODE COMMENTED OUT BELOW
        # ========================================================
        # suspended_count = 0
        # error_count = 0
        # 
        # for member in expired_members:
        #     days_overdue = (today - member.subscription_due_date).days
        #     
        #     if dry_run:
        #         self.stdout.write(
        #             self.style.WARNING(
        #                 f'[DRY RUN] Would suspend: {member.email} '
        #                 f'(expired {days_overdue} days ago on {member.subscription_due_date})'
        #             )
        #         )
        #         suspended_count += 1
        #     else:
        #         # Suspend the member
        #         reason = (
        #             f'Annual subscription expired on {member.subscription_due_date}. '
        #             f'Please pay your subscription fee to reactivate your account.'
        #         )
        #         
        #         # Create a system user for the suspension (or use None)
        #         success, message, _ = MemberManagementService.suspend_member(
        #             member.id,
        #             reason,
        #             None  # System-initiated suspension
        #         )
        #         
        #         if success:
        #             self.stdout.write(
        #                 self.style.SUCCESS(
        #                     f'Suspended: {member.email} '
        #                     f'(expired {days_overdue} days ago on {member.subscription_due_date})'
        #                 )
        #             )
        #             suspended_count += 1
        #             logger.info(f'Auto-suspended member {member.email} due to expired subscription')
        #         else:
        #             self.stdout.write(
        #                 self.style.ERROR(
        #                     f'Failed to suspend {member.email}: {message}'
        #                 )
        #             )
        #             error_count += 1
        #             logger.error(f'Failed to auto-suspend member {member.email}: {message}')
        # 
        # # Summary
        # self.stdout.write(self.style.SUCCESS('\n--- Summary ---'))
        # if dry_run:
        #     self.stdout.write(self.style.WARNING(f'DRY RUN MODE - No changes made'))
        # self.stdout.write(self.style.SUCCESS(f'Total expired: {count}'))
        # self.stdout.write(self.style.SUCCESS(f'Suspended: {suspended_count}'))
        # if error_count > 0:
        #     self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
