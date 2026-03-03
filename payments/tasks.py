"""
Celery tasks for payment processing.
Background tasks for polling fallback and payment monitoring.
"""
import logging
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from payments.models import Payment
from payments.services.hybrid_payment_service import HybridPaymentService

logger = logging.getLogger(__name__)


@shared_task(
    name='payments.poll_pending_payments',
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def poll_pending_payments(self, max_payments=50):
    """
    Celery task to poll pending payments as fallback.
    
    This task should run every 10-15 seconds to check payments
    that haven't received webhook notifications.
    
    Args:
        max_payments: Maximum number of payments to check per run
    
    Returns:
        Dict with task results
    """
    try:
        logger.info(f"Starting payment polling task (max: {max_payments})")
        
        # Use management command for consistency
        call_command('poll_pending_payments', '--max-payments', str(max_payments))
        
        logger.info("Payment polling task completed successfully")
        return {
            'success': True,
            'message': 'Polling completed',
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            f"Payment polling task failed: {str(e)}",
            exc_info=True
        )
        # Retry task
        raise self.retry(exc=e)


@shared_task(
    name='payments.check_timeout_payments',
    bind=True
)
def check_timeout_payments(self):
    """
    Check for payments that have exceeded total timeout.
    Mark them as timeout if still pending.
    
    Runs every 5 minutes to catch any payments that slipped through.
    """
    try:
        logger.info("Checking for timeout payments")
        
        # Find payments older than 2 minutes still pending
        cutoff_time = timezone.now() - timedelta(seconds=120)
        
        timeout_payments = Payment.objects.filter(
            status__in=[Payment.STATUS_PENDING, Payment.STATUS_PROCESSING],
            created_at__lt=cutoff_time
        )
        
        count = 0
        for payment in timeout_payments:
            payment.mark_timeout()
            count += 1
            logger.warning(
                f"Payment marked as timeout",
                extra={
                    "payment_id": str(payment.id),
                    "transaction_reference": payment.transaction_reference,
                    "age_seconds": (timezone.now() - payment.created_at).total_seconds()
                }
            )
        
        logger.info(f"Timeout check completed: {count} payment(s) marked as timeout")
        
        return {
            'success': True,
            'timeout_count': count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            f"Timeout check task failed: {str(e)}",
            exc_info=True
        )
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(
    name='payments.cleanup_old_webhook_notifications',
    bind=True
)
def cleanup_old_webhook_notifications(self, days=30):
    """
    Clean up old webhook notifications to prevent database bloat.
    
    Runs daily to remove webhook notifications older than specified days.
    
    Args:
        days: Number of days to keep notifications (default: 30)
    """
    try:
        from payments.models_webhook import WebhookNotification
        
        logger.info(f"Cleaning up webhook notifications older than {days} days")
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        deleted_count, _ = WebhookNotification.objects.filter(
            received_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"Cleanup completed: {deleted_count} notification(s) deleted")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(
            f"Cleanup task failed: {str(e)}",
            exc_info=True
        )
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(
    name='payments.generate_webhook_stats',
    bind=True
)
def generate_webhook_stats(self):
    """
    Generate statistics about webhook vs polling usage.
    
    Useful for monitoring webhook reliability and optimizing configuration.
    Runs hourly.
    """
    try:
        from payments.models_webhook import PaymentStatusCheck
        
        logger.info("Generating webhook statistics")
        
        # Get stats for last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        webhook_checks = PaymentStatusCheck.objects.filter(
            check_type='webhook',
            checked_at__gte=one_hour_ago
        ).count()
        
        polling_checks = PaymentStatusCheck.objects.filter(
            check_type='polling',
            checked_at__gte=one_hour_ago
        ).count()
        
        total_checks = webhook_checks + polling_checks
        webhook_percentage = (webhook_checks / total_checks * 100) if total_checks > 0 else 0
        
        stats = {
            'success': True,
            'period': 'last_hour',
            'webhook_checks': webhook_checks,
            'polling_checks': polling_checks,
            'total_checks': total_checks,
            'webhook_percentage': round(webhook_percentage, 2),
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(
            f"Webhook stats: {webhook_checks} webhook, {polling_checks} polling "
            f"({webhook_percentage:.1f}% webhook)"
        )
        
        return stats
        
    except Exception as e:
        logger.error(
            f"Stats generation failed: {str(e)}",
            exc_info=True
        )
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


# ============================================================================
# CELERY BEAT SCHEDULE
# ============================================================================

"""
Add this to your celery.py or settings.py:

from celery.schedules import crontab

app.conf.beat_schedule = {
    # Poll pending payments every 15 seconds
    'poll-pending-payments': {
        'task': 'payments.poll_pending_payments',
        'schedule': 15.0,
        'options': {
            'expires': 10.0,
        }
    },
    
    # Check for timeout payments every 5 minutes
    'check-timeout-payments': {
        'task': 'payments.check_timeout_payments',
        'schedule': crontab(minute='*/5'),
    },
    
    # Clean up old webhook notifications daily at 2 AM
    'cleanup-webhook-notifications': {
        'task': 'payments.cleanup_old_webhook_notifications',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {'days': 30}
    },
    
    # Generate webhook stats every hour
    'generate-webhook-stats': {
        'task': 'payments.generate_webhook_stats',
        'schedule': crontab(minute=0),
    },
}
"""
