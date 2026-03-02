"""
Payment service layer for orchestrating payment operations.
Abstracts provider-specific logic and provides a unified interface
for payment initiation, status checking, webhooks, and retries.
"""
import logging
from decimal import Decimal
from typing import Tuple, Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.utils import timezone

from payments.models import Payment, PaymentConfig
from payments.services.mtn_service import MTNService
from payments.services.airtel_service import AirtelService
from payments.utils import PhoneNumberEncryption, validate_phone_number
from payments.logging_utils import (
    set_correlation_id,
    get_correlation_id,
    log_payment_event,
    create_log_context,
    PerformanceLoggingMixin
)

User = get_user_model()
logger = logging.getLogger(__name__)


class PaymentService(PerformanceLoggingMixin):
    """
    Service layer for payment operations.
    Orchestrates payment initiation, status checking, webhooks, and retries.
    Abstracts provider-specific logic (MTN, Airtel).
    """
    
    def __init__(self):
        """Initialize payment service with provider services."""
        self.mtn_service = MTNService()
        self.airtel_service = AirtelService()
        self.phone_encryptor = PhoneNumberEncryption()
    
    def _get_provider_service(self, provider: str):
        """
        Get the appropriate provider service instance.
        
        Args:
            provider: Provider name ('mtn' or 'airtel')
        
        Returns:
            Provider service instance
        
        Raises:
            ValueError: If provider is not supported
        """
        if provider == Payment.PROVIDER_MTN:
            return self.mtn_service
        elif provider == Payment.PROVIDER_AIRTEL:
            return self.airtel_service
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _get_currency(self, provider: str) -> str:
        """
        Get the appropriate currency based on provider and environment.
        
        MTN sandbox only supports EUR, but production uses UGX.
        Airtel supports UGX in both sandbox and production.
        
        Args:
            provider: Provider name ('mtn' or 'airtel')
        
        Returns:
            Currency code ('EUR' or 'UGX')
        """
        import os
        
        # Get environment from settings
        environment = os.getenv('PAYMENT_ENVIRONMENT', 'sandbox')
        
        # MTN sandbox requires EUR, production uses UGX
        if provider == Payment.PROVIDER_MTN and environment == 'sandbox':
            return 'EUR'
        
        # All other cases use UGX (Airtel sandbox/production, MTN production)
        return 'UGX'
    
    @PerformanceLoggingMixin.log_performance('payment_initiation')
    def initiate_payment(
        self,
        user: Optional[User],
        phone_number: str,
        amount: Decimal,
        provider: str,
        application_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[Payment], str]:
        """
        Initiate a payment request.
        
        Steps:
        1. Validate phone number format
        2. Validate amount
        3. Create Payment record with status='pending'
        4. Encrypt phone number before storage
        5. Call provider service to initiate payment
        6. Update Payment record with transaction reference
        7. Handle errors and return result
        
        Args:
            user: User making the payment (None for registration payments)
            phone_number: User's phone number (256XXXXXXXXX)
            amount: Payment amount
            provider: Payment provider ('mtn' or 'airtel')
            application_id: Optional application ID to link payment
            ip_address: Optional IP address for audit
            user_agent: Optional user agent for audit
        
        Returns:
            Tuple of (success, payment_object, message)
            - success: True if payment initiated successfully
            - payment_object: Payment instance (or None if failed)
            - message: Success or error message
        
        Requirements: 1.3, 1.4, 3.1
        """
        # Set correlation ID for this payment flow
        correlation_id = set_correlation_id()
        
        try:
            # Step 1: Validate phone number format
            is_valid, error_message = validate_phone_number(phone_number)
            if not is_valid:
                logger.warning(
                    f"Invalid phone number format",
                    extra={
                        "user_id": user.id if user else None,
                        "provider": provider,
                        "error": error_message
                    }
                )
                return False, None, error_message
            
            # Step 2: Validate amount
            if amount <= 0:
                return False, None, "Amount must be greater than zero"
            
            # Step 3: Encrypt phone number
            encrypted_phone = self.phone_encryptor.encrypt(phone_number)
            
            # Step 4: Generate unique transaction reference
            import uuid
            transaction_reference = str(uuid.uuid4())
            
            # Step 5: Create Payment record with status='pending'
            payment = Payment.objects.create(
                user=user,
                phone_number=encrypted_phone,
                amount=amount,
                currency=self._get_currency(provider),
                provider=provider,
                transaction_reference=transaction_reference,
                status=Payment.STATUS_PENDING,
                application_id=application_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Step 5a: Link payment to application if application_id provided
            if application_id:
                try:
                    from applications.models import Application
                    application = Application.objects.get(id=application_id)
                    application.current_payment = payment
                    application.payment_transaction_reference = transaction_reference
                    application.payment_status = 'pending'
                    application.save()
                    
                    logger.info(
                        f"Payment linked to application",
                        extra={
                            "payment_id": str(payment.id),
                            "application_id": application_id,
                            "transaction_reference": transaction_reference
                        }
                    )
                except Application.DoesNotExist:
                    logger.warning(
                        f"Application not found for payment link",
                        extra={
                            "payment_id": str(payment.id),
                            "application_id": application_id
                        }
                    )
            
            # Log payment creation with structured logging
            log_payment_event(
                logger=logger,
                event_type='initiated',
                payment_id=str(payment.id),
                transaction_reference=transaction_reference,
                provider=provider,
                status=Payment.STATUS_PENDING,
                amount=str(amount),
                user_id=user.id if user else None,
                masked_phone=self.phone_encryptor.mask(phone_number)
            )
            
            # Step 6: Call provider service to initiate payment
            try:
                provider_service = self._get_provider_service(provider)
                
                # Get appropriate currency for provider and environment
                currency = self._get_currency(provider)
                
                # Airtel requires a separate transaction_id parameter
                if provider == Payment.PROVIDER_AIRTEL:
                    result = provider_service.request_to_pay(
                        phone_number=phone_number,
                        amount=amount,
                        currency=currency,
                        reference=transaction_reference,
                        transaction_id=transaction_reference
                    )
                else:
                    # MTN uses reference only
                    result = provider_service.request_to_pay(
                        phone_number=phone_number,
                        amount=amount,
                        currency=currency,
                        reference=transaction_reference,
                        payer_message="APF Membership Fee"
                    )
                
                if result.get('success'):
                    # Payment request sent successfully
                    logger.info(
                        f"Payment request sent to provider",
                        extra={
                            "payment_id": str(payment.id),
                            "transaction_reference": transaction_reference,
                            "provider": provider
                        }
                    )
                    return True, payment, result.get('message', 'Payment request sent')
                else:
                    # Provider returned error
                    error_msg = result.get('message', 'Payment request failed')
                    payment.mark_failed(error_msg, result)
                    
                    logger.error(
                        f"Provider rejected payment request",
                        extra={
                            "payment_id": str(payment.id),
                            "transaction_reference": transaction_reference,
                            "provider": provider,
                            "error": error_msg
                        }
                    )
                    return False, payment, error_msg
                    
            except ValueError as e:
                # Provider not supported
                payment.mark_failed(str(e))
                logger.error(
                    f"Unsupported provider",
                    extra={
                        "payment_id": str(payment.id),
                        "provider": provider,
                        "error": str(e)
                    }
                )
                return False, payment, str(e)
            
            except Exception as e:
                # Unexpected error during provider call
                error_msg = f"Payment initiation failed: {str(e)}"
                payment.mark_failed(error_msg)
                
                logger.error(
                    f"Payment initiation exception",
                    extra={
                        "payment_id": str(payment.id),
                        "transaction_reference": transaction_reference,
                        "provider": provider,
                        "error": str(e)
                    },
                    exc_info=True
                )
                return False, payment, "Payment service temporarily unavailable. Please try again."
        
        except Exception as e:
            # Unexpected error before payment record creation
            logger.error(
                f"Payment initiation failed before record creation",
                extra={
                    "user_id": user.id if user else None,
                    "provider": provider,
                    "error": str(e)
                },
                exc_info=True
            )
            return False, None, "Payment service error. Please try again."
    
    @PerformanceLoggingMixin.log_performance('payment_status_check')
    def check_payment_status(self, payment: Payment) -> Tuple[str, str]:
        """
        Check current status of a payment.
        
        Steps:
        1. Determine provider from Payment record
        2. Call provider's status check method
        3. Update Payment record based on response
        4. Return normalized status
        
        Args:
            payment: Payment instance to check status for
        
        Returns:
            Tuple of (status, message)
            - status: Current payment status ('pending', 'completed', 'failed', etc.)
            - message: Status message for display
        
        Requirements: 1.6, 1.7, 1.8, 3.2, 2.6, 2.7, 2.8
        """
        try:
            # Step 1: Get provider service
            provider_service = self._get_provider_service(payment.provider)
            
            # Step 2: Call provider's status check
            # Airtel uses transaction_id, MTN uses transaction_reference
            # Both are stored in transaction_reference field
            result = provider_service.check_payment_status(payment.transaction_reference)
            
            if not result.get('success'):
                # Status check failed (network error, etc.)
                logger.warning(
                    f"Payment status check failed",
                    extra={
                        "payment_id": str(payment.id),
                        "transaction_reference": payment.transaction_reference,
                        "provider": payment.provider,
                        "error": result.get('message')
                    }
                )
                return payment.status, result.get('message', 'Status check failed')
            
            # Step 3: Update Payment record based on response
            status = result.get('status')
            message = result.get('message', '')
            provider_tx_id = result.get('provider_transaction_id')
            response_data = result.get('raw_response')
            
            if status == 'completed' and payment.status != Payment.STATUS_COMPLETED:
                # Payment completed
                payment.mark_completed(provider_tx_id, response_data)
                
                # Update linked application if exists
                if payment.application_id:
                    try:
                        from applications.models import Application
                        application = Application.objects.get(id=payment.application_id)
                        application.payment_status = 'success'
                        
                        # Auto-submit (approve) application after successful payment
                        if application.status == 'pending':
                            application.status = 'approved'
                            logger.info(
                                f"Application auto-approved after successful payment",
                                extra={
                                    "payment_id": str(payment.id),
                                    "application_id": payment.application_id
                                }
                            )
                        
                        application.save()
                        
                        logger.info(
                            f"Application payment status updated to success",
                            extra={
                                "payment_id": str(payment.id),
                                "application_id": payment.application_id
                            }
                        )
                    except Application.DoesNotExist:
                        logger.warning(
                            f"Application not found for payment completion update",
                            extra={
                                "payment_id": str(payment.id),
                                "application_id": payment.application_id
                            }
                        )
                
                logger.info(
                    f"Payment completed",
                    extra={
                        "payment_id": str(payment.id),
                        "transaction_reference": payment.transaction_reference,
                        "provider": payment.provider,
                        "provider_transaction_id": provider_tx_id
                    }
                )
            
            elif status == 'failed' and payment.status != Payment.STATUS_FAILED:
                # Payment failed
                payment.mark_failed(message, response_data)
                
                # Update linked application if exists
                if payment.application_id:
                    try:
                        from applications.models import Application
                        application = Application.objects.get(id=payment.application_id)
                        application.payment_status = 'failed'
                        application.payment_error_message = message
                        application.save()
                        
                        logger.info(
                            f"Application payment status updated to failed",
                            extra={
                                "payment_id": str(payment.id),
                                "application_id": payment.application_id
                            }
                        )
                    except Application.DoesNotExist:
                        logger.warning(
                            f"Application not found for payment failure update",
                            extra={
                                "payment_id": str(payment.id),
                                "application_id": payment.application_id
                            }
                        )
                
                logger.info(
                    f"Payment failed",
                    extra={
                        "payment_id": str(payment.id),
                        "transaction_reference": payment.transaction_reference,
                        "provider": payment.provider,
                        "error": message
                    }
                )
            
            elif status == 'pending' and payment.status == Payment.STATUS_PENDING:
                # Still pending, update to processing if provider says so
                if response_data and response_data.get('status') == 'PENDING':
                    payment.status = Payment.STATUS_PROCESSING
                    payment.save()
            
            # Step 4: Return current status
            return payment.status, message
        
        except ValueError as e:
            # Provider not supported
            logger.error(
                f"Unsupported provider for status check",
                extra={
                    "payment_id": str(payment.id),
                    "provider": payment.provider,
                    "error": str(e)
                }
            )
            return payment.status, str(e)
        
        except Exception as e:
            # Unexpected error
            logger.error(
                f"Payment status check exception",
                extra={
                    "payment_id": str(payment.id),
                    "transaction_reference": payment.transaction_reference,
                    "provider": payment.provider,
                    "error": str(e)
                },
                exc_info=True
            )
            return payment.status, "Status check failed. Please try again."
    
    def process_webhook(
        self,
        provider: str,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Process webhook callback from payment provider.
        
        Steps:
        1. Verify webhook signature
        2. Extract transaction reference from payload
        3. Find Payment record by transaction reference
        4. Update status based on webhook data (idempotently)
        5. Return success/failure
        
        Args:
            provider: Payment provider ('mtn' or 'airtel')
            payload: Webhook payload dictionary
            signature: Webhook signature from headers
        
        Returns:
            True if webhook processed successfully, False otherwise
        
        Requirements: 3.6, 3.7, 8.3, 8.4, 8.8
        """
        try:
            # Step 1: Get provider service and verify signature
            provider_service = self._get_provider_service(provider)
            
            # Convert payload to string for signature verification
            import json
            payload_str = json.dumps(payload, sort_keys=True)
            
            if not provider_service.verify_webhook_signature(payload_str, signature):
                logger.warning(
                    f"Webhook signature verification failed",
                    extra={
                        "provider": provider,
                        "payload_keys": list(payload.keys())
                    }
                )
                return False
            
            # Step 2: Extract transaction reference from payload
            # MTN uses 'referenceId', Airtel uses 'transaction.id'
            if provider == Payment.PROVIDER_MTN:
                transaction_reference = payload.get('referenceId')
            elif provider == Payment.PROVIDER_AIRTEL:
                transaction_data = payload.get('transaction', {})
                transaction_reference = transaction_data.get('id')
            else:
                logger.error(f"Unknown provider in webhook: {provider}")
                return False
            
            if not transaction_reference:
                logger.error(
                    f"No transaction reference in webhook payload",
                    extra={"provider": provider, "payload": payload}
                )
                return False
            
            # Step 3: Find Payment record
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
                return False
            
            # Step 4: Update status based on webhook data (idempotently)
            # Check if payment is already in a terminal state
            if payment.status in [Payment.STATUS_COMPLETED, Payment.STATUS_CANCELLED]:
                # Already processed, return success (idempotency)
                logger.info(
                    f"Webhook for already completed payment (idempotent)",
                    extra={
                        "payment_id": str(payment.id),
                        "transaction_reference": transaction_reference,
                        "current_status": payment.status
                    }
                )
                return True
            
            # Extract status from webhook payload
            if provider == Payment.PROVIDER_MTN:
                webhook_status = payload.get('status', '').upper()
                provider_tx_id = payload.get('financialTransactionId')
                
                if webhook_status == 'SUCCESSFUL':
                    payment.mark_completed(provider_tx_id, payload)
                    
                    # Update linked application if exists
                    if payment.application_id:
                        try:
                            from applications.models import Application
                            application = Application.objects.get(id=payment.application_id)
                            application.payment_status = 'success'
                            
                            # Auto-submit (approve) application after successful payment
                            if application.status == 'pending':
                                application.status = 'approved'
                                logger.info(
                                    f"Webhook: Application auto-approved after successful payment",
                                    extra={
                                        "payment_id": str(payment.id),
                                        "application_id": payment.application_id
                                    }
                                )
                            
                            application.save()
                        except Application.DoesNotExist:
                            pass
                    
                    logger.info(
                        f"Webhook: Payment completed",
                        extra={
                            "payment_id": str(payment.id),
                            "transaction_reference": transaction_reference,
                            "provider_transaction_id": provider_tx_id
                        }
                    )
                elif webhook_status == 'FAILED':
                    error_reason = payload.get('reason', 'Payment failed')
                    payment.mark_failed(error_reason, payload)
                    
                    # Update linked application if exists
                    if payment.application_id:
                        try:
                            from applications.models import Application
                            application = Application.objects.get(id=payment.application_id)
                            application.payment_status = 'failed'
                            application.payment_error_message = error_reason
                            application.save()
                        except Application.DoesNotExist:
                            pass
                    
                    logger.info(
                        f"Webhook: Payment failed",
                        extra={
                            "payment_id": str(payment.id),
                            "transaction_reference": transaction_reference,
                            "error": error_reason
                        }
                    )
            
            elif provider == Payment.PROVIDER_AIRTEL:
                transaction_data = payload.get('transaction', {})
                webhook_status = transaction_data.get('status', '').upper()
                provider_tx_id = transaction_data.get('id')
                
                if webhook_status == 'TS':  # Transaction Successful
                    payment.mark_completed(provider_tx_id, payload)
                    
                    # Update linked application if exists
                    if payment.application_id:
                        try:
                            from applications.models import Application
                            application = Application.objects.get(id=payment.application_id)
                            application.payment_status = 'success'
                            
                            # Auto-submit (approve) application after successful payment
                            if application.status == 'pending':
                                application.status = 'approved'
                                logger.info(
                                    f"Webhook: Application auto-approved after successful payment",
                                    extra={
                                        "payment_id": str(payment.id),
                                        "application_id": payment.application_id
                                    }
                                )
                            
                            application.save()
                        except Application.DoesNotExist:
                            pass
                    
                    logger.info(
                        f"Webhook: Payment completed",
                        extra={
                            "payment_id": str(payment.id),
                            "transaction_reference": transaction_reference,
                            "provider_transaction_id": provider_tx_id
                        }
                    )
                elif webhook_status in ['TF', 'TA']:  # Transaction Failed/Ambiguous
                    error_message = transaction_data.get('message', 'Payment failed')
                    payment.mark_failed(error_message, payload)
                    
                    # Update linked application if exists
                    if payment.application_id:
                        try:
                            from applications.models import Application
                            application = Application.objects.get(id=payment.application_id)
                            application.payment_status = 'failed'
                            application.payment_error_message = error_message
                            application.save()
                        except Application.DoesNotExist:
                            pass
                    
                    logger.info(
                        f"Webhook: Payment failed",
                        extra={
                            "payment_id": str(payment.id),
                            "transaction_reference": transaction_reference,
                            "error": error_message
                        }
                    )
            
            # Step 5: Return success
            return True
        
        except ValueError as e:
            # Provider not supported
            logger.error(
                f"Unsupported provider in webhook",
                extra={"provider": provider, "error": str(e)}
            )
            return False
        
        except Exception as e:
            # Unexpected error
            logger.error(
                f"Webhook processing exception",
                extra={
                    "provider": provider,
                    "error": str(e)
                },
                exc_info=True
            )
            return False

    def retry_payment(self, payment: Payment) -> Tuple[bool, Optional[Payment], str]:
        """
        Retry a failed payment.
        
        Steps:
        1. Check if payment can be retried
        2. Decrypt phone number from original payment
        3. Create new Payment record with same details
        4. Initiate payment with provider
        5. Return result
        
        Args:
            payment: Original Payment instance to retry
        
        Returns:
            Tuple of (success, new_payment_object, message)
            - success: True if retry initiated successfully
            - new_payment_object: New Payment instance (or None if failed)
            - message: Success or error message
        
        Requirements: 12.1, 12.2
        """
        try:
            # Step 1: Check if payment can be retried
            if not payment.can_retry():
                return False, None, f"Payment cannot be retried. Current status: {payment.status}"
            
            # Step 2: Decrypt phone number from original payment
            decrypted_phone = self.phone_encryptor.decrypt(payment.phone_number)
            
            # Step 3: Initiate new payment with same details
            logger.info(
                f"Retrying payment",
                extra={
                    "original_payment_id": str(payment.id),
                    "original_transaction_reference": payment.transaction_reference,
                    "provider": payment.provider,
                    "amount": str(payment.amount)
                }
            )
            
            success, new_payment, message = self.initiate_payment(
                user=payment.user,
                phone_number=decrypted_phone,
                amount=payment.amount,
                provider=payment.provider,
                application_id=payment.application_id,
                ip_address=payment.ip_address,
                user_agent=payment.user_agent
            )
            
            if success:
                logger.info(
                    f"Payment retry successful",
                    extra={
                        "original_payment_id": str(payment.id),
                        "new_payment_id": str(new_payment.id),
                        "new_transaction_reference": new_payment.transaction_reference
                    }
                )
            else:
                logger.warning(
                    f"Payment retry failed",
                    extra={
                        "original_payment_id": str(payment.id),
                        "error": message
                    }
                )
            
            return success, new_payment, message
        
        except Exception as e:
            logger.error(
                f"Payment retry exception",
                extra={
                    "payment_id": str(payment.id),
                    "error": str(e)
                },
                exc_info=True
            )
            return False, None, "Retry failed. Please try again."
    
    def cancel_payment(self, payment: Payment) -> bool:
        """
        Cancel a pending payment.
        
        Steps:
        1. Check if payment is still pending
        2. Update status to 'cancelled'
        3. Return success
        
        Args:
            payment: Payment instance to cancel
        
        Returns:
            True if payment cancelled successfully, False otherwise
        
        Requirements: 12.3, 12.4
        """
        try:
            # Step 1: Check if payment is still pending
            if payment.status not in [Payment.STATUS_PENDING, Payment.STATUS_PROCESSING]:
                logger.warning(
                    f"Cannot cancel payment with status {payment.status}",
                    extra={
                        "payment_id": str(payment.id),
                        "transaction_reference": payment.transaction_reference,
                        "status": payment.status
                    }
                )
                return False
            
            # Step 2: Update status to 'cancelled'
            payment.status = Payment.STATUS_CANCELLED
            payment.error_message = "Payment cancelled by user"
            payment.save()
            
            logger.info(
                f"Payment cancelled",
                extra={
                    "payment_id": str(payment.id),
                    "transaction_reference": payment.transaction_reference
                }
            )
            
            # Step 3: Return success
            return True
        
        except Exception as e:
            logger.error(
                f"Payment cancellation exception",
                extra={
                    "payment_id": str(payment.id),
                    "error": str(e)
                },
                exc_info=True
            )
            return False
    
    def get_membership_fee(self) -> Decimal:
        """
        Get current membership fee from configuration.
        
        Returns:
            Membership fee amount as Decimal
        
        Requirements: 13.1, 13.2
        """
        try:
            return PaymentConfig.get_membership_fee()
        except Exception as e:
            logger.error(
                f"Failed to get membership fee",
                extra={"error": str(e)},
                exc_info=True
            )
            # Return default fallback
            return Decimal('50000.00')
