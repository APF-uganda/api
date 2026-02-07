"""
End-to-end integration test for failed MTN payment flow.
Tests the complete flow: initiate payment → poll status → fail.
Verifies error handling and retry capability.

Requirements: 1.8, 6.1-6.10, 12.1
"""
import pytest
import uuid
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


class TestFailedPaymentE2E:
    """End-to-end test for failed payment flow."""
    
    def test_failed_payment_insufficient_funds(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test payment failure due to insufficient funds.
        Verifies error message and retry capability.
        
        Requirements: 1.8, 6.5, 12.1
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
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
            
            # Step 2: Poll status - returns failed with insufficient funds
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Insufficient funds in your MTN Mobile Money account',
                'provider_transaction_id': None,
                'raw_response': {
                    'status': 'FAILED',
                    'reason': 'NOT_ENOUGH_FUNDS'
                }
            }
            
            status, message = payment_service.check_payment_status(payment)
            
            # Step 3: Verify payment marked as failed
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_FAILED
            assert payment.error_message is not None
            assert 'insufficient funds' in payment.error_message.lower()
            assert payment.completed_at is None
            assert payment.provider_transaction_id is None
            
            # Step 4: Verify payment can be retried
            assert payment.can_retry() is True
    
    def test_failed_payment_user_cancelled(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test payment failure when user cancels on their phone.
        
        Requirements: 1.8, 6.4
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
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
            
            # Poll status - user cancelled
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Payment cancelled by user',
                'provider_transaction_id': None,
                'raw_response': {
                    'status': 'FAILED',
                    'reason': 'PAYER_CANCELLED'
                }
            }
            
            status, message = payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Verify failure
            assert payment.status == Payment.STATUS_FAILED
            assert payment.error_message is not None
            assert payment.can_retry() is True
    
    def test_failed_payment_invalid_phone(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test payment failure due to invalid/unregistered phone number.
        
        Requirements: 1.8, 6.2
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
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
            
            # Poll status - phone not registered
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Phone number not registered with MTN Mobile Money',
                'provider_transaction_id': None,
                'raw_response': {
                    'status': 'FAILED',
                    'reason': 'PAYER_NOT_FOUND'
                }
            }
            
            status, message = payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Verify failure
            assert payment.status == Payment.STATUS_FAILED
            assert 'not registered' in payment.error_message.lower()
            assert payment.can_retry() is True
    
    def test_failed_payment_with_retry(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test complete flow: payment fails → user retries → new payment created.
        
        Requirements: 12.1, 12.2, 12.5
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref_1 = str(uuid.uuid4())
        transaction_ref_2 = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # Step 1: Initiate first payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref_1,
                'message': 'Payment request sent'
            }
            
            success, payment1, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            assert success is True
            original_payment_id = payment1.id
            
            # Step 2: Payment fails
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Insufficient funds',
                'provider_transaction_id': None,
                'raw_response': {'status': 'FAILED', 'reason': 'NOT_ENOUGH_FUNDS'}
            }
            
            status, message = payment_service.check_payment_status(payment1)
            payment1.refresh_from_db()
            
            assert payment1.status == Payment.STATUS_FAILED
            
            # Step 3: Retry payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref_2,
                'message': 'Payment request sent'
            }
            
            success, payment2, message = payment_service.retry_payment(payment1)
            
            # Step 4: Verify new payment created
            assert success is True
            assert payment2 is not None
            assert payment2.id != payment1.id  # Different payment record
            assert payment2.transaction_reference != payment1.transaction_reference
            assert payment2.status == Payment.STATUS_PENDING
            
            # Verify same details
            assert payment2.user == payment1.user
            assert payment2.amount == payment1.amount
            assert payment2.currency == payment1.currency
            assert payment2.provider == payment1.provider
            
            # Verify original payment unchanged
            payment1.refresh_from_db()
            assert payment1.status == Payment.STATUS_FAILED
            
            # Step 5: Complete the retry
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed',
                'provider_transaction_id': 'MTN-TX-RETRY-123',
                'raw_response': {
                    'status': 'SUCCESSFUL',
                    'financialTransactionId': 'MTN-TX-RETRY-123'
                }
            }
            
            status, message = payment_service.check_payment_status(payment2)
            payment2.refresh_from_db()
            
            assert payment2.status == Payment.STATUS_COMPLETED
            assert payment2.provider_transaction_id == 'MTN-TX-RETRY-123'
    
    def test_failed_payment_network_error(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test handling of network error during status check.
        
        Requirements: 6.3, 6.8
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
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
            
            # Simulate network error during status check
            mock_check_status.return_value = {
                'success': False,
                'status': 'pending',
                'message': 'Network error. Please check your connection and try again.',
                'provider_transaction_id': None
            }
            
            status, message = payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Payment should remain pending (not marked as failed)
            assert payment.status == Payment.STATUS_PENDING
            assert 'network' in message.lower() or 'connection' in message.lower()
    
    def test_failed_payment_provider_error(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test handling of provider service error.
        
        Requirements: 6.1, 6.8
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
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
            
            # Simulate provider service error
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Payment service temporarily unavailable',
                'provider_transaction_id': None,
                'raw_response': {
                    'status': 'FAILED',
                    'reason': 'SERVICE_UNAVAILABLE'
                }
            }
            
            status, message = payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Verify failure with appropriate message
            assert payment.status == Payment.STATUS_FAILED
            assert 'unavailable' in payment.error_message.lower() or 'service' in payment.error_message.lower()
            assert payment.can_retry() is True
    
    def test_failed_payment_multiple_polls_then_fail(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test payment that stays pending for several polls then fails.
        
        Requirements: 1.6, 1.8, 4.1-4.4
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
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
            
            # Simulate multiple pending polls
            for i in range(3):
                mock_check_status.return_value = {
                    'success': True,
                    'status': 'pending',
                    'message': 'Payment is pending',
                    'provider_transaction_id': None,
                    'raw_response': {'status': 'PENDING'}
                }
                
                status, message = payment_service.check_payment_status(payment)
                payment.refresh_from_db()
                assert payment.status in [Payment.STATUS_PENDING, Payment.STATUS_PROCESSING]
            
            # Final poll returns failure
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Payment cancelled by user',
                'provider_transaction_id': None,
                'raw_response': {'status': 'FAILED', 'reason': 'PAYER_CANCELLED'}
            }
            
            status, message = payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Verify final failure
            assert payment.status == Payment.STATUS_FAILED
            assert payment.error_message is not None
            assert payment.can_retry() is True
