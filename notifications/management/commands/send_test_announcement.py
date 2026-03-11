"""
Management command to send a test announcement to all members
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.models import Announcement
from notifications.announcement_services import create_in_app_notifications, get_announcement_recipients
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send a test announcement to all members'

    def add_arguments(self, parser):
        parser.add_argument(
            '--title',
            type=str,
            default='Test Announcement',
            help='Title of the test announcement'
        )
        parser.add_argument(
            '--content',
            type=str,
            default='This is a test announcement to verify the notification system is working properly.',
            help='Content of the test announcement'
        )
        parser.add_argument(
            '--audience',
            type=str,
            default='members',
            choices=['all_users', 'members', 'applicants', 'admins'],
            help='Target audience for the announcement'
        )

    def handle(self, *args, **options):
        # Get an admin user to create the announcement
        admin_user = User.objects.filter(role='1').first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No admin user found. Please create an admin user first.')
            )
            return

        # Create the test announcement
        announcement = Announcement.objects.create(
            title=options['title'],
            content=options['content'],
            audience=options['audience'],
            channel='in_app',  # Just in-app for testing
            status='sent',
            priority='medium',
            created_by=admin_user
        )

        # Create in-app notifications
        create_in_app_notifications(announcement)

        recipient_count = get_announcement_recipients(announcement).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Test announcement "{announcement.title}" sent to {announcement.audience} audience. '
                f'Created in-app notifications for {recipient_count} users.'
            )
        )
