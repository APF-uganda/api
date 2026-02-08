"""
End-to-end integration test for webhook processing.
Tests the complete flow: initiate payment → receive webhook → update status.
Verifies idempotency with duplicate webhooks.

Requirements: 8.1-8.8
"""
import pytest
import uuid
import json
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model

from payments.models import Payment, PaymentConfig
from payments.services.payment_service import PaymentService

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        email='testuser@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def membership_fee_config(db):
    """Create membership fee configuration."""
    config, created = PaymentConfig.objects.get_or_create(
        key='membership_fee_ugx',
        defaults={
            'value': '50000',
            'description': 'APF membership fee in UGX'
        }
    )
    return config


@pytest.fixture
def payment_service():
    """Create payment service instance."""
    return PaymentService()


class TestWebhookProcessingE2E:
    """End-to-end test for webhook processing."""
    
    def test_webhook_successful_payment(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test webhook processing for successful payment.
        
        Requirements: 8.1, 8.3, 8.4, 8.7
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'verify_webhook_signature') as mock_verify_signature:
            
            # Step 1: Initiate payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref,
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            assert success is True
            assert payment.status == Payment.STATUS_PENDING
            
            # Use the actual transaction reference from the created payment
            actual_transaction_ref = payment.transaction_reference
            
            # Step 2: Receive webhook with successful status
            webhook_payload = {
                'referenceId': actual_transaction_ref,
                'status': 'SUCCESSFUL',
                'financialTransactionId': 'MTN-WEBHOOK-TX-123',
                'amount': '50000',
                'currency': 'UGX'
            }
            
            # Mock signature verification
            mock_verify_signature.return_value = True
            
            # Process webhook
            result = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload,
                signature='valid-signature'
            )
            
            # Step 3: Verify webhook processed successfully
            assert result is True
            
            # Step 4: Verify payment status updated
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_COMPLETED
            assert payment.provider_transaction_id == 'MTN-WEBHOOK-TX-123'
            assert payment.completed_at is not None
            assert payment.provider_response is not None
            assert payment.provider_response['status'] == 'SUCCESSFUL'
    
    def test_webhook_failed_payment(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test webhook processing for failed payment.
        
        Requirements: 8.1, 8.3, 8.4
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'verify_webhook_signature') as mock_verify_signature:
            
            # Initiate payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref,
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            assert success is True
            
            # Use actual transaction reference
            actual_transaction_ref = payment.transaction_reference
            
            # Receive webhook with failed status
            webhook_payload = {
                'referenceId': actual_transaction_ref,
                'status': 'FAILED',
                'reason': 'NOT_ENOUGH_FUNDS',
                'amount': '50000',
                'currency': 'UGX'
            }
            
            mock_verify_signature.return_value = True
            
            # Process webhook
            result = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload,
                signature='valid-signature'
            )
            
            # Verify webhook processed
            assert result is True
            
            # Verify payment status updated to failed
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_FAILED
            assert payment.error_message is not None
            assert payment.completed_at is None
            assert payment.provider_transaction_id is None
    
    def test_webhook_idempotency(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that duplicate webhooks are handled idempotently.
        Processing the same webhook multiple times should produce same result.
        
        Requirements: 8.8
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'verify_webhook_signature') as mock_verify_signature:
            
            # Initiate payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref,
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Use actual transaction reference
            actual_transaction_ref = payment.transaction_reference
            
            # Webhook payload
            webhook_payload = {
                'referenceId': actual_transaction_ref,
                'status': 'SUCCESSFUL',
                'financialTransactionId': 'MTN-IDEMPOTENT-TX',
                'amount': '50000',
                'currency': 'UGX'
            }
            
            mock_verify_signature.return_value = True
            
            # Process webhook first time
            result1 = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload,
                signature='valid-signature'
            )
            
            assert result1 is True
            payment.refresh_from_db()
            
            # Capture state after first webhook
            first_status = payment.status
            first_provider_tx_id = payment.provider_transaction_id
            first_completed_at = payment.completed_at
            first_updated_at = payment.updated_at
            
            assert first_status == Payment.STATUS_COMPLETED
            assert first_provider_tx_id == 'MTN-IDEMPOTENT-TX'
            
            # Process same webhook second time (duplicate delivery)
            result2 = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload,
                signature='valid-signature'
            )
            
            assert result2 is True
            payment.refresh_from_db()
            
            # Verify state unchanged (idempotent)
            assert payment.status == first_status
            assert payment.provider_transaction_id == first_provider_tx_id
            assert payment.completed_at == first_completed_at
            
            # Process webhook third time
            result3 = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload,
                signature='valid-signature'
            )
            
            assert result3 is True
            payment.refresh_from_db()
            
            # Still unchanged
            assert payment.status == first_status
            assert payment.provider_transaction_id == first_provider_tx_id
    
    def test_webhook_invalid_signature(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that webhook with invalid signature is rejected.
        
        Requirements: 8.3, 8.4
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'verify_webhook_signature') as mock_verify_signature:
            
            # Initiate payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref,
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Webhook with invalid signature
            webhook_payload = {
                'referenceId': transaction_ref,
                'status': 'SUCCESSFUL',
                'financialTransactionId': 'MTN-INVALID-SIG',
            }
            
            # Mock signature verification failure
            mock_verify_signature.return_value = False
            
            # Process webhook
            result = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload,
                signature='invalid-signature'
            )
            
            # Webhook should be rejected
            assert result is False
            
            # Payment status should remain unchanged
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_PENDING
            assert payment.provider_transaction_id is None
    
    def test_webhook_for_nonexistent_payment(
        self,
        payment_service
    ):
        """
        Test webhook for payment that doesn't exist in database.
        
        Requirements: 8.5
        """
        # Random transaction reference that doesn't exist
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'verify_webhook_signature') as mock_verify_signature:
            
            webhook_payload = {
                'referenceId': transaction_ref,
                'status': 'SUCCESSFUL',
                'financialTransactionId': 'MTN-NONEXISTENT',
            }
            
            mock_verify_signature.return_value = True
            
            # Process webhook
            result = payment_service.process_webhook(
                provider=Payment.PROVIDER_MTN,
                payload=webhook_payload,
                signature='valid-signature'
            )
            
            # Webhook should fail (payment not found)
            assert result is False
    
    def test_webhook_updates_pending_payment_only(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that webhook only updates payments in pending/processing state.
        Completed payments should not be updated again.
        
        Requirements: 8.8
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'verify_webhook_signature') as mock_verify_signature:
            
            # Initiate payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref,
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Use actual transaction reference
            actual_transaction_ref = payment.transaction_reference
            
            # First webhook - completes payment
            webhook_payload_1 = {
                'referenceId': actual_transaction_ref,
                'status': 'SUCCESSFUL',
                'financialTransactionId': 'MTN-FIRST-TX',
            }
            
            mock_verify_signature.return_value = True
            
            result = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload_1,
                signature='valid-signature'
            )
            
            assert result is True
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_COMPLETED
            assert payment.provider_transaction_id == 'MTN-FIRST-TX'
            
            # Second webhook with different transaction ID
            # (shouldn't update completed payment)
            webhook_payload_2 = {
                'referenceId': actual_transaction_ref,
                'status': 'SUCCESSFUL',
                'financialTransactionId': 'MTN-SECOND-TX',
            }
            
            result = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload_2,
                signature='valid-signature'
            )
            
            # Should still return True (idempotent)
            assert result is True
            
            payment.refresh_from_db()
            # Transaction ID should remain unchanged
            assert payment.provider_transaction_id == 'MTN-FIRST-TX'
            assert payment.status == Payment.STATUS_COMPLETED
    
    def test_webhook_with_polling_race_condition(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test scenario where webhook arrives while polling is happening.
        Both should update payment correctly without conflicts.
        
        Requirements: 8.1, 8.4
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status, \
             patch.object(payment_service.mtn_service, 'verify_webhook_signature') as mock_verify_signature:
            
            # Initiate payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref,
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Use actual transaction reference
            actual_transaction_ref = payment.transaction_reference
            
            # Simulate polling (returns pending)
            mock_check_status.return_value = {
                'success': True,
                'status': 'pending',
                'message': 'Payment is pending',
                'provider_transaction_id': None,
                'raw_response': {'status': 'PENDING'}
            }
            
            payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            assert payment.status in [Payment.STATUS_PENDING, Payment.STATUS_PROCESSING]
            
            # Webhook arrives (completes payment)
            webhook_payload = {
                'referenceId': actual_transaction_ref,
                'status': 'SUCCESSFUL',
                'financialTransactionId': 'MTN-RACE-TX',
            }
            
            mock_verify_signature.return_value = True
            
            result = payment_service.process_webhook(
                provider=provider,
                payload=webhook_payload,
                signature='valid-signature'
            )
            
            assert result is True
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_COMPLETED
            assert payment.provider_transaction_id == 'MTN-RACE-TX'
            
            # Another poll happens (returns completed)
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed',
                'provider_transaction_id': 'MTN-RACE-TX',
                'raw_response': {
                    'status': 'SUCCESSFUL',
                    'financialTransactionId': 'MTN-RACE-TX'
                }
            }
            
            payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Should still be completed with same transaction ID
            assert payment.status == Payment.STATUS_COMPLETED
            assert payment.provider_transaction_id == 'MTN-RACE-TX'
