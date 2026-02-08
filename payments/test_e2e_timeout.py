"""
End-to-end integration test for payment timeout scenario.
Tests the complete flow: initiate payment → poll for 90 seconds → timeout.
Verifies timeout handling.

Requirements: 1.9, 4.6
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


class TestPaymentTimeoutE2E:
    """End-to-end test for payment timeout scenario."""
    
    def test_payment_timeout_after_multiple_polls(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test payment that remains pending and eventually times out.
        Simulates 30 polls (90 seconds at 3 seconds per poll).
        
        Requirements: 1.9, 4.6
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
            
            # Step 2: Simulate 30 polls (90 seconds) - all return pending
            # This simulates user not responding to payment prompt
            mock_check_status.return_value = {
                'success': True,
                'status': 'pending',
                'message': 'Payment is pending approval',
                'provider_transaction_id': None,
                'raw_response': {'status': 'PENDING'}
            }
            
            # Poll 30 times (simulating 90 seconds)
            for poll_count in range(30):
                status, message = payment_service.check_payment_status(payment)
                payment.refresh_from_db()
                
                # Should remain pending/processing throughout
                assert payment.status in [Payment.STATUS_PENDING, Payment.STATUS_PROCESSING]
                assert payment.completed_at is None
            
            # Step 3: After 30 polls, manually mark as timeout
            # (In real implementation, frontend would stop polling and mark as timeout)
            payment.mark_timeout()
            payment.refresh_from_db()
            
            # Step 4: Verify timeout status
            assert payment.status == Payment.STATUS_TIMEOUT
            assert payment.error_message is not None
            assert 'timeout' in payment.error_message.lower() or 'timed out' in payment.error_message.lower()
            assert payment.completed_at is None
            assert payment.provider_transaction_id is None
            
            # Step 5: Verify payment can be retried after timeout
            assert payment.can_retry() is True
    
    def test_timeout_payment_can_be_retried(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that a timed-out payment can be retried successfully.
        
        Requirements: 1.9, 12.1, 12.2
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
            
            # Step 2: Simulate timeout (payment stays pending)
            mock_check_status.return_value = {
                'success': True,
                'status': 'pending',
                'message': 'Payment is pending',
                'provider_transaction_id': None,
                'raw_response': {'status': 'PENDING'}
            }
            
            # Poll several times
            for _ in range(5):
                payment_service.check_payment_status(payment1)
            
            # Mark as timeout
            payment1.mark_timeout()
            payment1.refresh_from_db()
            assert payment1.status == Payment.STATUS_TIMEOUT
            
            # Step 3: Retry the payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref_2,
                'message': 'Payment request sent'
            }
            
            success, payment2, message = payment_service.retry_payment(payment1)
            
            # Step 4: Verify new payment created
            assert success is True
            assert payment2 is not None
            assert payment2.id != payment1.id
            assert payment2.transaction_reference != payment1.transaction_reference
            assert payment2.status == Payment.STATUS_PENDING
            
            # Verify original payment unchanged
            payment1.refresh_from_db()
            assert payment1.status == Payment.STATUS_TIMEOUT
            
            # Step 5: Complete the retry
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed',
                'provider_transaction_id': 'MTN-TX-TIMEOUT-RETRY',
                'raw_response': {
                    'status': 'SUCCESSFUL',
                    'financialTransactionId': 'MTN-TX-TIMEOUT-RETRY'
                }
            }
            
            status, message = payment_service.check_payment_status(payment2)
            payment2.refresh_from_db()
            
            assert payment2.status == Payment.STATUS_COMPLETED
            assert payment2.provider_transaction_id == 'MTN-TX-TIMEOUT-RETRY'
    
    def test_timeout_with_late_completion(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test scenario where payment completes after timeout period.
        This can happen if user approves payment after frontend stops polling.
        
        Requirements: 1.9, 4.6
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
            
            # Simulate timeout (stays pending for 30 polls)
            mock_check_status.return_value = {
                'success': True,
                'status': 'pending',
                'message': 'Payment is pending',
                'provider_transaction_id': None,
                'raw_response': {'status': 'PENDING'}
            }
            
            # Poll 30 times
            for _ in range(30):
                payment_service.check_payment_status(payment)
            
            # Mark as timeout
            payment.mark_timeout()
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_TIMEOUT
            
            # Simulate late completion (user approved after timeout)
            # If we check status again, it might show completed
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed',
                'provider_transaction_id': 'MTN-TX-LATE',
                'raw_response': {
                    'status': 'SUCCESSFUL',
                    'financialTransactionId': 'MTN-TX-LATE'
                }
            }
            
            # Check status again (e.g., via webhook or manual check)
            status, message = payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Payment should now be completed
            assert payment.status == Payment.STATUS_COMPLETED
            assert payment.provider_transaction_id == 'MTN-TX-LATE'
            assert payment.completed_at is not None
    
    def test_timeout_error_message(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that timeout error message is user-friendly.
        
        Requirements: 6.7
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay:
            
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
            
            # Mark as timeout
            payment.mark_timeout()
            payment.refresh_from_db()
            
            # Verify error message is user-friendly
            assert payment.error_message is not None
            assert 'timeout' in payment.error_message.lower() or 'timed out' in payment.error_message.lower()
            # Should mention checking phone or trying again
            assert '90 seconds' in payment.error_message or 'verification' in payment.error_message.lower()
    
    def test_timeout_preserves_payment_data(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that timeout preserves all payment data for audit trail.
        
        Requirements: 3.1, 3.2
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        ip_address = '192.168.1.100'
        user_agent = 'Mozilla/5.0'
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay:
            
            # Initiate payment with audit fields
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref,
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            original_created_at = payment.created_at
            original_transaction_ref = payment.transaction_reference
            
            # Mark as timeout
            payment.mark_timeout()
            payment.refresh_from_db()
            
            # Verify all data preserved
            assert payment.status == Payment.STATUS_TIMEOUT
            assert payment.user == test_user
            assert payment.amount == amount
            assert payment.currency == 'UGX'
            assert payment.provider == provider
            assert payment.transaction_reference == original_transaction_ref
            assert payment.created_at == original_created_at
            assert payment.ip_address == ip_address
            assert payment.user_agent == user_agent
            # Phone number should still be encrypted
            assert payment.phone_number != phone_number
