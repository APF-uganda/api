"""
Management command to link existing payments to users and applications
Run this to fix orphaned payments that don't have user/application links
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from payments.models import Payment
from applications.models import Application
from django.db.models import Q

User = get_user_model()


class Command(BaseCommand):
    help = 'Link existing payments to users and applications based on phone numbers and timing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes (preview mode)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('Linking orphaned payments to users and applications'))
        self.stdout.write('=' * 70)
        
        # Find completed payments without user links
        orphaned_payments = Payment.objects.filter(
            status=Payment.STATUS_COMPLETED,
            user__isnull=True
        ).order_by('-created_at')
        
        count = orphaned_payments.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No orphaned payments found'))
            return
        
        self.stdout.write(f'Found {count} orphaned payment(s)')
        self.stdout.write('')
        
        linked_count = 0
        skipped_count = 0
        
        for payment in orphaned_payments:
            self.stdout.write(f"\nProcessing payment: {payment.transaction_reference}")
            self.stdout.write(f"  Amount: {payment.amount} {payment.currency}")
            self.stdout.write(f"  Provider: {payment.provider}")
            self.stdout.write(f"  Created: {payment.created_at}")
            
            # Try to find matching application by amount and timing
            # Look for applications created around the same time with matching payment amount
            time_window_start = payment.created_at - timedelta(hours=24)
            time_window_end = payment.created_at + timedelta(hours=1)
            
            matching_applications = Application.objects.filter(
                payment_amount=payment.amount,
                submitted_at__gte=time_window_start,
                submitted_at__lte=time_window_end,
                payment_status__in=['pending', 'success']
            ).order_by('-submitted_at')
            
            if matching_applications.exists():
                application = matching_applications.first()
                
                self.stdout.write(
                    self.style.WARNING(
                        f"  → Found matching application: {application.first_name} {application.last_name} "
                        f"(ID: {application.id})"
                    )
                )
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [DRY RUN] Would link to user: {application.user.email if application.user else 'No user'}"
                        )
                    )
                else:
                    # Link payment to application and user
                    payment.application = application
                    if application.user:
                        payment.user = application.user
                    payment.save()
                    
                    # Update application payment status
                    application.current_payment = payment
                    application.payment_transaction_reference = payment.transaction_reference
                    application.payment_status = 'success'
                    application.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Linked to {application.user.email if application.user else 'application only'}"
                        )
                    )
                
                linked_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ✗ No matching application found"
                    )
                )
                skipped_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write('=' * 70)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes made'))
        
        self.stdout.write(f'Total orphaned payments: {count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully linked: {linked_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped (no match): {skipped_count}'))
        
        if not dry_run and linked_count > 0:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ Payments have been linked!'))
            self.stdout.write('')
            self.stdout.write('Linked payments will now show up in:')
            self.stdout.write('  - Recent Payments dashboard')
            self.stdout.write('  - Admin approval page payment status')
            self.stdout.write('  - User payment history')

