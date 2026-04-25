"""
Management command: send_renewal_reminders

Sends in-app and email renewal reminders to members whose subscription
is due in 14 days, 7 days, 1 day, or is already overdue (weekly after due date).

Usage:
    python manage.py send_renewal_reminders
    python manage.py send_renewal_reminders --dry-run
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from authentication.models import User
from notifications.models import UserNotification
from authentication.email_service_smtp import EmailService
import logging

logger = logging.getLogger(__name__)

REMINDER_DAYS = [14, 7, 1]  # Days before due date to send reminders


class Command(BaseCommand):
    help = 'Send membership renewal reminders to members with upcoming or overdue subscriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate without sending notifications or emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no notifications will be sent'))

        # Get all active members with a subscription_due_date
        members = User.objects.filter(
            role='2',
            is_active=True,
            subscription_due_date__isnull=False,
        )

        sent = 0
        skipped = 0

        for member in members:
            due_date = member.subscription_due_date
            days_remaining = (due_date - today).days

            # Determine if we should notify today.
            # For upcoming: notify at exactly 14, 7, and 1 day(s) before due.
            # For overdue: notify once a week (every 7 days after the due date).
            if days_remaining >= 0:
                should_notify = days_remaining in REMINDER_DAYS
            else:
                overdue_days = abs(days_remaining)
                should_notify = overdue_days % 7 == 0

            if not should_notify:
                skipped += 1
                continue

            user_name = member.first_name or member.email.split('@')[0]
            due_date_str = due_date.strftime('%d %B %Y')
            frontend_url = 'https://apfuganda.org'
            renewal_url = f"{frontend_url}/payments"

            # Build notification message
            if days_remaining > 0:
                title = f"Membership Renewal Due in {days_remaining} Day{'s' if days_remaining != 1 else ''}"
                message = (
                    f"Your APF Uganda membership subscription is due on {due_date_str}. "
                    f"Please renew your membership to avoid suspension."
                )
                priority = 'high' if days_remaining <= 7 else 'medium'
            else:
                overdue_days = abs(days_remaining)
                title = "Membership Renewal Overdue"
                message = (
                    f"Your APF Uganda membership subscription was due on {due_date_str} "
                    f"({overdue_days} day{'s' if overdue_days != 1 else ''} ago). "
                    f"Please renew immediately to avoid account suspension."
                )
                priority = 'high'

            if not dry_run:
                # In-app notification
                UserNotification.objects.create(
                    user=member,
                    title=title,
                    message=message,
                    notification_type='warning',
                    priority=priority,
                    metadata={'renewal_url': renewal_url, 'due_date': str(due_date)},
                )

                # Email notification
                EmailService.send_renewal_reminder_email(
                    email=member.email,
                    user_name=user_name,
                    due_date=due_date_str,
                    days_remaining=max(days_remaining, 0),
                    renewal_url=renewal_url,
                )

            sent += 1
            self.stdout.write(
                f"  {'[DRY RUN] ' if dry_run else ''}Notified {member.email} "
                f"({'overdue' if days_remaining < 0 else f'{days_remaining}d remaining'})"
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone — notified: {sent}, skipped: {skipped}"
        ))
