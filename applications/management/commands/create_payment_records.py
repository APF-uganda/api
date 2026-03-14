"""
Management command to create payment records for existing applications.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from applications.models import Application
from payments.models import ManualPayment


class Command(BaseCommand):
    help = 'Create payment records for existing applications that do not have them'

    def handle(self, *args, **options):
        """Create payment records for applications without them."""
        
        # Get all applications that don't have payment records
        applications_without_payments = Application.objects.filter(
            manual_payments__isnull=True
        ).distinct()
        
        created_count = 0
        
        for app in applications_without_payments:
            try:
                with transaction.atomic():
                    # Determine payment status based on application status
                    if app.status == 'approved':
                        payment_status = ManualPayment.STATUS_VERIFIED
                    elif app.status == 'rejected':
                        payment_status = ManualPayment.STATUS_REJECTED
                    else:
                        payment_status = ManualPayment.STATUS_PENDING
                    
                    # Create payment record
                    payment = ManualPayment.objects.create(
                        application=app,
                        user=app.user,  # May be None for some applications
                        amount=app.payment_amount or 50000.00,
                        currency='UGX',
                        reference=app.application_id,
                        description='Application Fee',
                        application_reference=app.application_id,
                        status=payment_status,
                        proof_of_payment=app.proof_of_payment_doc,
                    )
                    
                    # Update timestamps to match application
                    payment.created_at = app.submitted_at
                    payment.updated_at = app.updated_at
                    payment.save(update_fields=['created_at', 'updated_at'])
                    
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created payment record for application {app.application_id}'
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to create payment record for application {app.application_id}: {e}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} payment records for existing applications'
            )
        )