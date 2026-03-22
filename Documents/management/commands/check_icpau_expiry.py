"""
Management command to check ICPAU certificate expiry and send notifications.
ICPAU certificates expire every December 31st.

Sends reminders at: 60, 30, 14, and 7 days before expiry
Marks certificates as expired after December 31st

Run daily via cron: python manage.py check_icpau_expiry
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from Documents.models import Document, MemberDocument
from notifications.models import UserNotification
from authentication.email_service_smtp import EmailService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check ICPAU certificate expiry and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without sending notifications or updating database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get current date and December 31st of current year
        today = timezone.now().date()
        current_year = today.year
        expiry_date = datetime(current_year, 12, 31).date()
        
        # If we're past December 31st, use next year
        if today > expiry_date:
            expiry_date = datetime(current_year + 1, 12, 31).date()

        days_until_expiry = (expiry_date - today).days
        
        self.stdout.write(f'Today: {today}')
        self.stdout.write(f'ICPAU Expiry Date: {expiry_date}')
        self.stdout.write(f'Days until expiry: {days_until_expiry}')
        
        # Reminder thresholds (60, 30, 14, 7 days)
        reminder_thresholds = [60, 30, 14, 7]
        
        # Check if today matches any reminder threshold
        should_send_reminder = days_until_expiry in reminder_thresholds
        
        if should_send_reminder:
            self.stdout.write(self.style.SUCCESS(
                f'Sending {days_until_expiry}-day reminder notifications'
            ))
            self._send_expiry_reminders(days_until_expiry, expiry_date, dry_run)
        else:
            self.stdout.write(f'No reminders scheduled for {days_until_expiry} days before expiry')
        
        # Mark expired certificates (after December 31st)
        if days_until_expiry < 0:
            self.stdout.write(self.style.WARNING('ICPAU certificates have expired'))
            self._mark_expired_certificates(dry_run)
        
        self.stdout.write(self.style.SUCCESS('ICPAU expiry check completed'))

    def _send_expiry_reminders(self, days_remaining, expiry_date, dry_run):
        """Send expiry reminder notifications to members with ICPAU certificates"""
        
        # Find all ICPAU certificates in MemberDocument
        icpau_docs = MemberDocument.objects.filter(
            Q(document_type__icontains='icpau') | Q(document_type__icontains='certificate'),
            status='approved'
        ).select_related('user')
        
        # Also check Application documents for ICPAU certificates
        app_icpau_docs = Document.objects.filter(
            Q(document_type__icontains='icpau') | Q(document_type__icontains='certificate'),
            status='approved',
            application__user__isnull=False
        ).select_related('application__user')

        # Collect unique users
        users_to_notify = set()
        
        for doc in icpau_docs:
            users_to_notify.add(doc.user)
        
        for doc in app_icpau_docs:
            if doc.application and doc.application.user:
                users_to_notify.add(doc.application.user)
        
        self.stdout.write(f'Found {len(users_to_notify)} members with ICPAU certificates')
        
        notification_count = 0
        email_count = 0
        
        for user in users_to_notify:
            # Create in-app notification
            if not dry_run:
                # Check if notification already sent today
                existing_notification = UserNotification.objects.filter(
                    user=user,
                    title__icontains='ICPAU Certificate Expiry',
                    created_at__date=timezone.now().date()
                ).exists()
                
                if not existing_notification:
                    UserNotification.objects.create(
                        user=user,
                        title='ICPAU Certificate Expiry Reminder',
                        message=self._get_notification_message(days_remaining, expiry_date),
                        notification_type='warning',
                        priority='high' if days_remaining <= 14 else 'medium'
                    )
                    notification_count += 1
            else:
                notification_count += 1
            
            # Send email notification
            if user.email_notifications_enabled:
                if not dry_run:
                    success = self._send_expiry_email(user, days_remaining, expiry_date)
                    if success:
                        email_count += 1
                else:
                    email_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Created {notification_count} in-app notifications'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Sent {email_count} email notifications'
        ))

    def _get_notification_message(self, days_remaining, expiry_date):
        """Generate notification message based on days remaining"""
        if days_remaining == 60:
            return (
                f'Your ICPAU certificate will expire on {expiry_date.strftime("%B %d, %Y")}. '
                f'You have {days_remaining} days to renew your certificate. '
                'Please upload your renewed ICPAU certificate to maintain your membership status.'
            )
        elif days_remaining == 30:
            return (
                f'Important: Your ICPAU certificate expires in {days_remaining} days on {expiry_date.strftime("%B %d, %Y")}. '
                'Please renew and upload your certificate as soon as possible.'
            )
        elif days_remaining == 14:
            return (
                f'Urgent: Your ICPAU certificate expires in {days_remaining} days on {expiry_date.strftime("%B %d, %Y")}. '
                'Please renew and upload your certificate immediately to avoid membership suspension.'
            )
        elif days_remaining == 7:
            return (
                f'Final Reminder: Your ICPAU certificate expires in {days_remaining} days on {expiry_date.strftime("%B %d, %Y")}. '
                'This is your last reminder. Please renew and upload your certificate now.'
            )
        else:
            return (
                f'Your ICPAU certificate will expire on {expiry_date.strftime("%B %d, %Y")}. '
                f'Please renew and upload your certificate.'
            )

    def _send_expiry_email(self, user, days_remaining, expiry_date):
        """Send email notification about certificate expiry"""
        try:
            user_name = user.get_full_name() if hasattr(user, 'get_full_name') else user.email.split('@')[0]
            
            # Use EmailService to send notification
            # For now, we'll use a simple text email
            # TODO: Create HTML template for ICPAU expiry notifications
            
            from django.core.mail import send_mail
            from django.conf import settings
            
            subject = f'ICPAU Certificate Expiry Reminder - {days_remaining} Days'
            message = self._get_notification_message(days_remaining, expiry_date)

            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
            
            logger.info(f'Sent ICPAU expiry email to {user.email}')
            return True
            
        except Exception as e:
            logger.error(f'Failed to send ICPAU expiry email to {user.email}: {str(e)}')
            return False

    def _mark_expired_certificates(self, dry_run):
        """Mark ICPAU certificates as expired after December 31st"""
        
        # Update MemberDocument ICPAU certificates
        member_docs = MemberDocument.objects.filter(
            Q(document_type__icontains='icpau') | Q(document_type__icontains='certificate'),
            status='approved'
        )
        
        # Update Application Document ICPAU certificates
        app_docs = Document.objects.filter(
            Q(document_type__icontains='icpau') | Q(document_type__icontains='certificate'),
            status='approved'
        )
        
        if not dry_run:
            member_count = member_docs.update(status='expired')
            app_count = app_docs.update(status='expired')
            
            self.stdout.write(self.style.WARNING(
                f'Marked {member_count} member ICPAU certificates as expired'
            ))
            self.stdout.write(self.style.WARNING(
                f'Marked {app_count} application ICPAU certificates as expired'
            ))
        else:
            self.stdout.write(f'Would mark {member_docs.count()} member certificates as expired')
            self.stdout.write(f'Would mark {app_docs.count()} application certificates as expired')
