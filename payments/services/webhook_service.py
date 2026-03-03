"""
Webhook-first payment status service with polling fallback.
Implements hybrid approach: webhooks as primary, polling as backup.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from payments.models import Payment
from payments.models_webhook import WebhookNotification, PaymentStatusCheck

logger = logging.getLogger(__name__)


class WebhookConfig:
    """Configuration for webhook-first with polling fallback."""
    
    # Timeout before falling back to polling (seconds)
    WEBHOOK_TIMEOUT = getattr(settings, 'PAYMENT_WEBHOOK_TIMEOUT', 60)
    
    # Polling interval when webhook not received (seconds)
    POLLING_INTERVAL = getattr(settings, 'PAYMENT_POLLING_INTERVAL', 10)
    
    # Maximum polling attempts before giving up
    MAX_POLLING_ATTEMPTS = getattr(settings, 'PAYMENT_MAX_POLLING_ATTEMPTS', 9)
    
    # Total timeout for payment verification (seconds)
    TOTAL_TIMEOUT = getattr(settings, 'PAYMENT_TOTAL_TIMEOUT', 90)


class WebhookStatusService:
    """
    Service for webhook-first payment status checking with polling fallback.
    
    Strategy:
    1. Wait for webhook notification (primary method)
    2. If webhook not received within timeout, fall back to polling
    3. Continue polling at intervals until status determined or timeout
    4. Track all status checks for audit trail
    """
    
    def __init__(self):
        """Initialize webhook status service."""
        self.config = WebhookConfig()
    
    def record_webhook_notification(
        self,
        payment: Payment,
        provider: str,
        payload: Dict[str, Any],
        signature: str,
        signature_valid: bool,
        webhook_status: str
    ) -> WebhookNotification:
        """
        Record incoming webhook notification.
        
        Args:
            payment: Payment instance
            provider: Payment provider ('mtn' or 'airtel')
            payload: Webhook payload dictionary
            signature: Webhook signature from headers
            signature_valid: Whether signature verification passed
            webhook_status: Status value from webhook payload
        
        Returns:
            WebhookNotification instance
        """
        notification = WebhookNotification.objects.create(
            payment=payment,
            provider=provider,
            transaction_reference=payment.transaction_reference,
            webhook_status=webhook_status,
            payload=payload,
            signature=signature,
            signature_valid=signature_valid,
            status=WebhookNotification.STATUS_RECEIVED
        )
        
        logger.info(
            f"Webhook notification recorded",
            extra={
                "payment_id": str(payment.id),
                "transaction_reference": payment.transaction_reference,
                "provider": provider,
                "webhook_status": webhook_status,
                "signature_valid": signature_valid
            }
        )
        
        return notification
    
    def has_received_webhook(self, payment: Payment) -> bool:
        """
        Check if payment has received any webhook notification.
        
        Args:
            payment: Payment instance
        
        Returns:
            True if webhook notification exists, False otherwise
        """
        return WebhookNotification.objects.filter(
            payment=payment,
            signature_valid=True
        ).exists()
    
    def should_use_polling_fallback(self, payment: Payment) -> bool:
        """
        Determine if polling fallback should be used.
        
        Polling is used when:
        1. No webhook received within timeout period
        2. Payment is still in pending/processing state
        3. Payment hasn't timed out completely
        
        Args:
            payment: Payment instance
        
        Returns:
            True if polling should be used, False otherwise
        """
        # Check if payment is in a terminal state
        if payment.status in [Payment.STATUS_COMPLETED, Payment.STATUS_FAILED, 
                              Payment.STATUS_CANCELLED, Payment.STATUS_TIMEOUT]:
            return False
        
        # Check if total timeout exceeded
        time_elapsed = (timezone.now() - payment.created_at).total_seconds()
        if time_elapsed > self.config.TOTAL_TIMEOUT:
            return False
        
        # Check if webhook received
        if self.has_received_webhook(payment):
            return False
        
        # Check if webhook timeout exceeded
        if time_elapsed > self.config.WEBHOOK_TIMEOUT:
            logger.info(
                f"Webhook timeout exceeded, enabling polling fallback",
                extra={
                    "payment_id": str(payment.id),
                    "transaction_reference": payment.transaction_reference,
                    "time_elapsed": time_elapsed,
                    "webhook_timeout": self.config.WEBHOOK_TIMEOUT
                }
            )
            return True
        
        return False
    
    def record_status_check(
        self,
        payment: Payment,
        check_type: str,
        status_before: str,
        status_after: str,
        success: bool,
        message: str = None,
        response_data: Dict[str, Any] = None
    ) -> PaymentStatusCheck:
        """
        Record a payment status check attempt.
        
        Args:
            payment: Payment instance
            check_type: Type of check ('webhook', 'polling', 'manual')
            status_before: Payment status before check
            status_after: Payment status after check
            success: Whether check was successful
            message: Optional message
            response_data: Optional response data
        
        Returns:
            PaymentStatusCheck instance
        """
        check = PaymentStatusCheck.objects.create(
            payment=payment,
            check_type=check_type,
            status_before=status_before,
            status_after=status_after,
            success=success,
            message=message,
            response_data=response_data
        )
        
        logger.debug(
            f"Status check recorded",
            extra={
                "payment_id": str(payment.id),
                "check_type": check_type,
                "status_before": status_before,
                "status_after": status_after,
                "success": success
            }
        )
        
        return check
    
    def get_polling_attempts_count(self, payment: Payment) -> int:
        """
        Get number of polling attempts for a payment.
        
        Args:
            payment: Payment instance
        
        Returns:
            Number of polling attempts
        """
        return PaymentStatusCheck.objects.filter(
            payment=payment,
            check_type=PaymentStatusCheck.TYPE_POLLING
        ).count()
    
    def should_poll_now(self, payment: Payment) -> bool:
        """
        Determine if payment should be polled now.
        
        Checks:
        1. Polling fallback is enabled
        2. Haven't exceeded max polling attempts
        3. Enough time passed since last poll
        
        Args:
            payment: Payment instance
        
        Returns:
            True if should poll now, False otherwise
        """
        # Check if polling fallback should be used
        if not self.should_use_polling_fallback(payment):
            return False
        
        # Check max attempts
        attempts = self.get_polling_attempts_count(payment)
        if attempts >= self.config.MAX_POLLING_ATTEMPTS:
            logger.warning(
                f"Max polling attempts reached",
                extra={
                    "payment_id": str(payment.id),
                    "attempts": attempts,
                    "max_attempts": self.config.MAX_POLLING_ATTEMPTS
                }
            )
            return False
        
        # Check time since last poll
        last_check = PaymentStatusCheck.objects.filter(
            payment=payment,
            check_type=PaymentStatusCheck.TYPE_POLLING
        ).order_by('-checked_at').first()
        
        if last_check:
            time_since_last = (timezone.now() - last_check.checked_at).total_seconds()
            if time_since_last < self.config.POLLING_INTERVAL:
                return False
        
        return True
    
    @transaction.atomic
    def process_webhook_update(
        self,
        notification: WebhookNotification,
        payment: Payment,
        new_status: str,
        provider_tx_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Process webhook notification and update payment status.
        
        This method is idempotent - safe to call multiple times.
        
        Args:
            notification: WebhookNotification instance
            payment: Payment instance
            new_status: New payment status
            provider_tx_id: Optional provider transaction ID
            error_message: Optional error message
        
        Returns:
            True if payment was updated, False if already in terminal state
        """
        status_before = payment.status
        
        # Check if payment already in terminal state (idempotency)
        if payment.status in [Payment.STATUS_COMPLETED, Payment.STATUS_CANCELLED]:
            logger.info(
                f"Payment already in terminal state, skipping webhook update",
                extra={
                    "payment_id": str(payment.id),
                    "current_status": payment.status,
                    "webhook_status": new_status
                }
            )
            notification.mark_processed()
            return False
        
        # Update payment based on new status
        try:
            if new_status == 'completed':
                payment.mark_completed(provider_tx_id, notification.payload)
            elif new_status == 'failed':
                payment.mark_failed(error_message or 'Payment failed', notification.payload)
            else:
                # Pending or other status - just update
                payment.status = new_status
                payment.save()
            
            # Mark notification as processed
            notification.mark_processed()
            
            # Record status check
            self.record_status_check(
                payment=payment,
                check_type=PaymentStatusCheck.TYPE_WEBHOOK,
                status_before=status_before,
                status_after=payment.status,
                success=True,
                message=f"Webhook processed: {notification.webhook_status}",
                response_data=notification.payload
            )
            
            logger.info(
                f"Payment updated via webhook",
                extra={
                    "payment_id": str(payment.id),
                    "status_before": status_before,
                    "status_after": payment.status,
                    "provider_tx_id": provider_tx_id
                }
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to process webhook: {str(e)}"
            notification.mark_failed(error_msg)
            
            logger.error(
                f"Webhook processing failed",
                extra={
                    "payment_id": str(payment.id),
                    "error": str(e)
                },
                exc_info=True
            )
            
            return False
