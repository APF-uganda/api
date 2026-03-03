"""
Management command to poll pending payments as fallback.
Run this as a scheduled task (cron/celery) every 10-15 seconds.
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from payments.models import Payment
from payments.services.hybrid_payment_service import HybridPaymentService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Poll pending payments that need fallback status checking'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--max-payments',
            type=int,
            default=50,
            help='Maximum number of payments to check per run'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be checked without actually checking'
        )
    
    def handle(self, *args, **options):
        """Poll pending payments that need status checking."""
        max_payments = options['max_payments']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting payment polling (max: {max_payments}, dry_run: {dry_run})"
            )
        )
        
        # Find payments that need polling
        payments_to_check = self._find_payments_needing_poll()
        
        if not payments_to_check:
            self.stdout.write("No payments need polling at this time")
            return
        
        self.stdout.write(
            f"Found {len(payments_to_check)} payment(s) that may need polling"
        )
        
        # Initialize service
        payment_service = HybridPaymentService()
        
        checked_count = 0
        updated_count = 0
        
        for payment in payments_to_check[:max_payments]:
            # Check if should poll this payment
            if not payment_service.webhook_service.should_poll_now(payment):
                continue
            
            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would check: {payment.transaction_reference} "
                    f"(status: {payment.status}, age: {self._get_age(payment)}s)"
                )
                checked_count += 1
                continue
            
            # Poll payment status
            try:
                status_before = payment.status
                status, message = payment_service.check_payment_status_hybrid(payment)
                checked_count += 1
                
                if status != status_before:
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Updated: {payment.transaction_reference} "
                            f"{status_before} → {status}"
                        )
                    )
                else:
                    self.stdout.write(
                        f"  Checked: {payment.transaction_reference} "
                        f"(still {status})"
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Error checking {payment.transaction_reference}: {str(e)}"
                    )
                )
                logger.error(
                    f"Polling command error",
                    extra={
                        "payment_id": str(payment.id),
                        "error": str(e)
                    },
                    exc_info=True
                )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted: {checked_count} checked, {updated_count} updated"
            )
        )
    
    def _find_payments_needing_poll(self):
        """
        Find payments that might need polling.
        
        Criteria:
        - Status is pending or processing
        - Created within last 2 minutes (120 seconds)
        - Not already completed/failed/cancelled/timeout
        """
        cutoff_time = timezone.now() - timedelta(seconds=120)
        
        return Payment.objects.filter(
            status__in=[Payment.STATUS_PENDING, Payment.STATUS_PROCESSING],
            created_at__gte=cutoff_time
        ).order_by('created_at')
    
    def _get_age(self, payment):
        """Get payment age in seconds."""
        return int((timezone.now() - payment.created_at).total_seconds())
