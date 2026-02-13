"""
Management command to process scheduled announcements
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from AdminNotifications.models import Announcement
from AdminNotifications.services import send_announcement_email, create_in_app_notifications
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process scheduled announcements that are ready to be sent'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Get scheduled announcements that are ready to be sent
        scheduled_announcements = Announcement.objects.filter(
            status='scheduled',
            scheduled_for__lte=now
        )
        
        if not scheduled_announcements.exists():
            self.stdout.write(
                self.style.SUCCESS('No scheduled announcements to process.')
            )
            return
        
        processed_count = 0
        for announcement in scheduled_announcements:
            try:
                # Update status to sent and set sent_at
                announcement.status = 'sent'
                announcement.sent_at = now
                announcement.save()
                
                # Send notifications
                send_announcement_email(announcement)
                create_in_app_notifications(announcement)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully processed scheduled announcement: {announcement.title}'
                    )
                )
                processed_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing announcement {announcement.title}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {processed_count} scheduled announcements.'
            )
        )