"""
Management command to send membership renewal invoices
Usage: python manage.py send_renewal_invoices [--all] [--email user@example.com]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.models import User
from admin_management.membership_renewal_service import MembershipRenewalService


class Command(BaseCommand):
    help = 'Send membership renewal invoice emails to members'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Send to all active members (annual renewal reminder)',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Send to specific email address',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting membership renewal invoice process...'))
        self.stdout.write('Note: All members receive annual renewal reminders regardless of join date')
        self.stdout.write('Membership year: April 1st to March 31st\n')
        
        # Determine which users to send to
        if options['email']:
            # Send to specific user
            try:
                user = User.objects.get(email=options['email'], is_active=True)
                users = [user]
                self.stdout.write(f"Sending to specific user: {user.email}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User not found: {options['email']}"))
                return
        
        elif options['all']:
            # Send to all active members
            users = MembershipRenewalService.get_all_active_members()
            self.stdout.write(f"Sending to all {users.count()} active members")
        
        else:
            self.stdout.write(self.style.ERROR('Please specify --all or --email'))
            self.stdout.write('\nExamples:')
            self.stdout.write('  python manage.py send_renewal_invoices --all')
            self.stdout.write('  python manage.py send_renewal_invoices --email user@example.com')
            return
        
        # Send invoices
        if len(users) == 1:
            # Single user
            user = users[0] if isinstance(users, list) else users.first()
            success, message = MembershipRenewalService.send_renewal_invoice_email(user)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ {message}'))
        
        else:
            # Multiple users
            results = MembershipRenewalService.send_bulk_renewal_invoices(users)
            
            self.stdout.write(self.style.SUCCESS(f"\nResults:"))
            self.stdout.write(f"  Total: {results['total']}")
            self.stdout.write(self.style.SUCCESS(f"  Success: {results['success_count']}"))
            
            if results['failed_count'] > 0:
                self.stdout.write(self.style.ERROR(f"  Failed: {results['failed_count']}"))
                
                # Show failed emails
                self.stdout.write(self.style.WARNING("\nFailed emails:"))
                for result in results['results']:
                    if not result['success']:
                        self.stdout.write(f"  ✗ {result['email']}: {result['message']}")
            
            self.stdout.write(self.style.SUCCESS('\nDone!'))
