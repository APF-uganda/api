"""
End-to-end integration test for payment retry flow.
Tests the complete flow: failed payment → retry → new payment created.
Verifies new transaction with same details.

Requirements: 12.1-12.7
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


class TestPaymentRetryE2E:
    """End-to-end test for payment retry flow."""
    
    def test_retry_failed_payment_creates_new_transaction(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that retrying a failed payment creates a new transaction.
        
        Requirements: 12.1, 12.2, 12.5
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # Step 1: Initiate first payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
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
            original_transaction_ref = payment1.transaction_reference
            
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
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment2, message = payment_service.retry_payment(payment1)
            
            # Step 4: Verify new payment created
            assert success is True
            assert payment2 is not None
            
            # New payment has different ID and transaction reference
            assert payment2.id != original_payment_id
            assert payment2.transaction_reference != original_transaction_ref
            
            # New payment has same details
            assert payment2.user == payment1.user
            assert payment2.amount == payment1.amount
            assert payment2.currency == payment1.currency
            assert payment2.provider == payment1.provider
            # Phone numbers should decrypt to same value (even if encrypted differently)
            from payments.utils import PhoneNumberEncryption
            encryptor = PhoneNumberEncryption()
            assert encryptor.decrypt(payment2.phone_number) == encryptor.decrypt(payment1.phone_number)
            
            # New payment starts as pending
            assert payment2.status == Payment.STATUS_PENDING
            
            # Original payment unchanged
            payment1.refresh_from_db()
            assert payment1.status == Payment.STATUS_FAILED
            assert payment1.id == original_payment_id
            assert payment1.transaction_reference == original_transaction_ref
    
    def test_retry_timeout_payment(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that retrying a timed-out payment works correctly.
        
        Requirements: 12.1, 12.2
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay:
            
            # Initiate first payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment1, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Mark as timeout
            payment1.mark_timeout()
            payment1.refresh_from_db()
            assert payment1.status == Payment.STATUS_TIMEOUT
            
            # Retry payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment2, message = payment_service.retry_payment(payment1)
            
            # Verify retry successful
            assert success is True
            assert payment2 is not None
            assert payment2.id != payment1.id
            assert payment2.status == Payment.STATUS_PENDING
            
            # Original payment still timeout
            payment1.refresh_from_db()
            assert payment1.status == Payment.STATUS_TIMEOUT
    
    def test_cannot_retry_completed_payment(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that completed payments cannot be retried.
        
        Requirements: 12.1
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # Initiate payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Complete payment
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed',
                'provider_transaction_id': 'MTN-TX-COMPLETE',
                'raw_response': {
                    'status': 'SUCCESSFUL',
                    'financialTransactionId': 'MTN-TX-COMPLETE'
                }
            }
            
            payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_COMPLETED
            
            # Try to retry completed payment
            success, new_payment, message = payment_service.retry_payment(payment)
            
            # Retry should fail
            assert success is False
            assert new_payment is None
            assert 'cannot be retried' in message.lower()
    
    def test_cannot_retry_pending_payment(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that pending payments cannot be retried.
        
        Requirements: 12.1
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay:
            
            # Initiate payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            assert payment.status == Payment.STATUS_PENDING
            
            # Try to retry pending payment
            success, new_payment, message = payment_service.retry_payment(payment)
            
            # Retry should fail
            assert success is False
            assert new_payment is None
            assert 'cannot be retried' in message.lower()
    
    def test_retry_preserves_audit_fields(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that retry preserves audit fields from original payment.
        
        Requirements: 12.5
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        ip_address = '192.168.1.100'
        user_agent = 'Mozilla/5.0'
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # Initiate payment with audit fields
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment1, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Fail payment
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Payment failed',
                'provider_transaction_id': None,
                'raw_response': {'status': 'FAILED'}
            }
            
            payment_service.check_payment_status(payment1)
            payment1.refresh_from_db()
            
            # Retry payment
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment2, message = payment_service.retry_payment(payment1)
            
            # Verify audit fields preserved
            assert success is True
            assert payment2.ip_address == ip_address
            assert payment2.user_agent == user_agent
    
    def test_retry_then_complete_successfully(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test complete retry flow: fail → retry → complete.
        
        Requirements: 12.1, 12.2, 12.5, 12.6
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # First attempt - fails
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment1, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Insufficient funds',
                'provider_transaction_id': None,
                'raw_response': {'status': 'FAILED', 'reason': 'NOT_ENOUGH_FUNDS'}
            }
            
            payment_service.check_payment_status(payment1)
            payment1.refresh_from_db()
            assert payment1.status == Payment.STATUS_FAILED
            
            # Retry
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment2, message = payment_service.retry_payment(payment1)
            assert success is True
            assert payment2.status == Payment.STATUS_PENDING
            
            # Complete retry
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed',
                'provider_transaction_id': 'MTN-RETRY-SUCCESS',
                'raw_response': {
                    'status': 'SUCCESSFUL',
                    'financialTransactionId': 'MTN-RETRY-SUCCESS'
                }
            }
            
            payment_service.check_payment_status(payment2)
            payment2.refresh_from_db()
            
            # Verify retry completed
            assert payment2.status == Payment.STATUS_COMPLETED
            assert payment2.provider_transaction_id == 'MTN-RETRY-SUCCESS'
            assert payment2.completed_at is not None
            
            # Original payment still failed
            payment1.refresh_from_db()
            assert payment1.status == Payment.STATUS_FAILED
            assert payment1.completed_at is None
    
    def test_multiple_retries(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that a payment can be retried multiple times.
        
        Requirements: 12.1, 12.2, 12.7
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # First attempt
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment1, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Fail first attempt
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Failed',
                'provider_transaction_id': None,
                'raw_response': {'status': 'FAILED'}
            }
            
            payment_service.check_payment_status(payment1)
            payment1.refresh_from_db()
            
            # First retry
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment2, message = payment_service.retry_payment(payment1)
            assert success is True
            
            # Fail second attempt
            payment_service.check_payment_status(payment2)
            payment2.refresh_from_db()
            
            # Second retry
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment3, message = payment_service.retry_payment(payment2)
            assert success is True
            
            # Verify all three payments exist and are different
            assert payment1.id != payment2.id != payment3.id
            assert payment1.transaction_reference != payment2.transaction_reference != payment3.transaction_reference
            
            # All have same user and amount
            assert payment1.user == payment2.user == payment3.user
            assert payment1.amount == payment2.amount == payment3.amount
    
    def test_retry_with_application_link(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test that retry preserves application link.
        
        Requirements: 12.5, 14.7
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        application_id = None  # Don't use foreign key
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # Initiate with application link
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment1, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider,
                application_id=application_id
            )
            
            # Fail payment
            mock_check_status.return_value = {
                'success': True,
                'status': 'failed',
                'message': 'Failed',
                'provider_transaction_id': None,
                'raw_response': {'status': 'FAILED'}
            }
            
            payment_service.check_payment_status(payment1)
            payment1.refresh_from_db()
            
            # Retry
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': str(uuid.uuid4()),
                'message': 'Payment request sent'
            }
            
            success, payment2, message = payment_service.retry_payment(payment1)
            
            # Verify application link preserved
            assert success is True
            assert payment2.application_id == application_id
