"""
Hybrid payment service with webhook-first and polling fallback.
Extends PaymentService with intelligent status checking strategy.
"""
import logging
from typing import Dict, Any, Tuple
from django.utils import timezone

from payments.models import Payment
from payments.services.payment_service import PaymentService
from payments.services.webhook_service import WebhookStatusService
from payments.services.mtn_service import MTNService
from payments.services.airtel_service import AirtelService

logger = logging.getLogger(__name__)


class HybridPaymentService(PaymentService):
    """
    Enhanced payment service with webhook-first, polling-fallback strategy.
    
    Features:
    - Webhook notifications processed immediately
    - Automatic polling fallback if webhook not received
    - Configurable timeouts and intervals
    - Complete audit trail of all status checks
    - Idempotent webhook processing
    """
    
    def __init__(self):
        """Initialize hybrid payment service."""
        super().__init__()
        self.webhook_service = WebhookStatusService()
    
    def check_payment_status_hybrid(self, payment: Payment) -> Tuple[str, str]:
        """
        Check payment status using hybrid webhook/polling approach.
        
        Strategy:
        1. Check if webhook already received → return current status
        2. Check if should use polling fallback → poll provider
        3. Otherwise wait for webhook → return current status
        
        Args:
            payment: Payment instance
        
        Returns:
            Tuple of (status, message)
        """
        # Refresh payment from database
        payment.refresh_from_db()
        
        # If payment in terminal state, return immediately
        if payment.status in [Payment.STATUS_COMPLETED, Payment.STATUS_FAILED,
                              Payment.STATUS_CANCELLED, Payment.STATUS_TIMEOUT]:
            return payment.status, self._get_status_message(payment.status)
        
        # Check if webhook received
        if self.webhook_service.has_received_webhook(payment):
            logger.debug(
                f"Webhook received, using webhook status",
                extra={
                    "payment_id": str(payment.id),
                    "status": payment.status
                }
            )
            return payment.status, self._get_status_message(payment.status)
        
        # Check if should use polling fallback
        if self.webhook_service.should_poll_now(payment):
            logger.info(
                f"Using polling fallback for payment status",
                extra={
                    "payment_id": str(payment.id),
                    "transaction_reference": payment.transaction_reference
                }
            )
            return self._poll_payment_status(payment)
        
        # Check if total timeout exceeded
        time_elapsed = (timezone.now() - payment.created_at).total_seconds()
        if time_elapsed > self.webhook_service.config.TOTAL_TIMEOUT:
            logger.warning(
                f"Payment verification timeout",
                extra={
                    "payment_id": str(payment.id),
                    "time_elapsed": time_elapsed
                }
            )
            payment.mark_timeout()
            return payment.status, "Payment verification timed out. Please contact support."
        
        # Still waiting for webhook
        return payment.status, "Payment is being processed. Please wait..."
    
    def _poll_payment_status(self, payment: Payment) -> Tuple[str, str]:
        """
        Poll provider for payment status (fallback method).
        
        Args:
            payment: Payment instance
        
        Returns:
            Tuple of (status, message)
        """
        status_before = payment.status
        
        try:
            # Use parent class method to check status
            status, message = super().check_payment_status(payment)
            
            # Record polling attempt
            self.webhook_service.record_status_check(
                payment=payment,
                check_type='polling',
                status_before=status_before,
                status_after=payment.status,
                success=True,
                message=message
            )
            
            logger.info(
                f"Polling status check completed",
                extra={
                    "payment_id": str(payment.id),
                    "status_before": status_before,
                    "status_after": status,
                    "polling_attempt": self.webhook_service.get_polling_attempts_count(payment)
                }
            )
            
            return status, message
            
        except Exception as e:
            logger.error(
                f"Polling status check failed",
                extra={
                    "payment_id": str(payment.id),
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Record failed polling attempt
            self.webhook_service.record_status_check(
                payment=payment,
                check_type='polling',
                status_before=status_before,
                status_after=payment.status,
                success=False,
                message=str(e)
            )
            
            return payment.status, "Status check failed. Please try again."
    
    def process_webhook_secure(
        self,
        provider: str,
        payload: Dict[str, Any],
        signature: str
    ) -> Tuple[bool, str, int]:
        """
        Process webhook with enhanced security and tracking.
        
        Args:
            provider: Payment provider ('mtn' or 'airtel')
            payload: Webhook payload dictionary
            signature: Webhook signature from headers
        
        Returns:
            Tuple of (success, message, http_status_code)
        """
        try:
            # Get provider service
            provider_service = self._get_provider_service(provider)
            
            # Verify signature
            import json
            payload_str = json.dumps(payload, sort_keys=True)
            signature_valid = provider_service.verify_webhook_signature(payload_str, signature)
            
            if not signature_valid:
                logger.warning(
                    f"Webhook signature verification failed",
                    extra={
                        "provider": provider,
                        "payload_keys": list(payload.keys())
                    }
                )
                return False, "Invalid signature", 401
            
            # Extract transaction reference
            transaction_reference = self._extract_transaction_reference(provider, payload)
            if not transaction_reference:
                logger.error(
                    f"No transaction reference in webhook",
                    extra={"provider": provider}
                )
                return False, "Missing transaction reference", 400
            
            # Find payment
            try:
                payment = Payment.objects.get(transaction_reference=transaction_reference)
            except Payment.DoesNotExist:
                logger.warning(
                    f"Payment not found for webhook",
                    extra={
                        "provider": provider,
                        "transaction_reference": transaction_reference
                    }
                )
                return False, "Payment not found", 404
            
            # Extract webhook status
            webhook_status, normalized_status, provider_tx_id, error_message = \
                self._extract_webhook_status(provider, payload)
            
            # Record webhook notification
            notification = self.webhook_service.record_webhook_notification(
                payment=payment,
                provider=provider,
                payload=payload,
                signature=signature,
                signature_valid=signature_valid,
                webhook_status=webhook_status
            )
            
            # Process webhook update (idempotent)
            updated = self.webhook_service.process_webhook_update(
                notification=notification,
                payment=payment,
                new_status=normalized_status,
                provider_tx_id=provider_tx_id,
                error_message=error_message
            )
            
            # Update linked application if payment completed
            if normalized_status == 'completed' and payment.application_id:
                self._update_application_status(payment, 'success')
            elif normalized_status == 'failed' and payment.application_id:
                self._update_application_status(payment, 'failed', error_message)
            
            message = "Webhook processed successfully" if updated else "Webhook already processed"
            return True, message, 200
            
        except Exception as e:
            logger.error(
                f"Webhook processing exception",
                extra={
                    "provider": provider,
                    "error": str(e)
                },
                exc_info=True
            )
            return False, "Internal server error", 500
    
    def _extract_transaction_reference(self, provider: str, payload: Dict[str, Any]) -> str:
        """Extract transaction reference from webhook payload."""
        if provider == Payment.PROVIDER_MTN:
            return payload.get('referenceId')
        elif provider == Payment.PROVIDER_AIRTEL:
            transaction_data = payload.get('transaction', {})
            return transaction_data.get('id')
        return None
    
    def _extract_webhook_status(
        self,
        provider: str,
        payload: Dict[str, Any]
    ) -> Tuple[str, str, str, str]:
        """
        Extract and normalize webhook status.
        
        Returns:
            Tuple of (webhook_status, normalized_status, provider_tx_id, error_message)
        """
        if provider == Payment.PROVIDER_MTN:
            webhook_status = payload.get('status', '').upper()
            provider_tx_id = payload.get('financialTransactionId')
            error_message = payload.get('reason', 'Payment failed')
            
            if webhook_status == 'SUCCESSFUL':
                normalized_status = 'completed'
            elif webhook_status == 'FAILED':
                normalized_status = 'failed'
            else:
                normalized_status = 'pending'
            
            return webhook_status, normalized_status, provider_tx_id, error_message
        
        elif provider == Payment.PROVIDER_AIRTEL:
            transaction_data = payload.get('transaction', {})
            webhook_status = transaction_data.get('status', '').upper()
            provider_tx_id = transaction_data.get('id')
            error_message = transaction_data.get('message', 'Payment failed')
            
            if webhook_status == 'TS':  # Transaction Successful
                normalized_status = 'completed'
            elif webhook_status in ['TF', 'TA']:  # Transaction Failed/Ambiguous
                normalized_status = 'failed'
            else:
                normalized_status = 'pending'
            
            return webhook_status, normalized_status, provider_tx_id, error_message
        
        return '', 'pending', None, None
    
    def _update_application_status(
        self,
        payment: Payment,
        status: str,
        error_message: str = None
    ):
        """Update linked application status."""
        try:
            from applications.models import Application
            application = Application.objects.get(id=payment.application_id)
            application.payment_status = status
            
            if status == 'success' and application.status == 'pending':
                application.status = 'approved'
                logger.info(
                    f"Application auto-approved after webhook",
                    extra={
                        "payment_id": str(payment.id),
                        "application_id": payment.application_id
                    }
                )
            
            if error_message:
                application.payment_error_message = error_message
            
            application.save()
            
        except Exception as e:
            logger.warning(
                f"Failed to update application status",
                extra={
                    "payment_id": str(payment.id),
                    "application_id": payment.application_id,
                    "error": str(e)
                }
            )
    
    def _get_status_message(self, status: str) -> str:
        """Get user-friendly message for payment status."""
        messages = {
            Payment.STATUS_PENDING: "Payment is pending approval",
            Payment.STATUS_PROCESSING: "Payment is being processed",
            Payment.STATUS_COMPLETED: "Payment completed successfully",
            Payment.STATUS_FAILED: "Payment failed",
            Payment.STATUS_TIMEOUT: "Payment verification timed out",
            Payment.STATUS_CANCELLED: "Payment was cancelled"
        }
        return messages.get(status, "Unknown status")
