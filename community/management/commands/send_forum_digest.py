"""
Management command to send forum digest emails
Usage:
    python manage.py send_forum_digest --frequency daily
    python manage.py send_forum_digest --frequency weekly
"""
from django.core.management.base import BaseCommand
from community.email_service import send_discussion_digest


class Command(BaseCommand):
    help = 'Send forum activity digest emails to members'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frequency',
            type=str,
            default='daily',
            choices=['daily', 'weekly'],
            help='Frequency of the digest (daily or weekly)'
        )

    def handle(self, *args, **options):
        frequency = options['frequency']
        
        self.stdout.write(self.style.SUCCESS(f'Sending {frequency} forum digest...'))
        
        try:
            send_discussion_digest(frequency=frequency)
            self.stdout.write(self.style.SUCCESS(f'✅ {frequency.capitalize()} digest sent successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error sending digest: {str(e)}'))
