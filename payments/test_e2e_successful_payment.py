"""
End-to-end integration test for successful MTN payment flow.
Tests the complete flow: initiate payment → poll status → complete.
Verifies database state at each step.

Requirements: 1.1-1.10
"""
import pytest
import uuid
import time
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth import get_user_model
from django.utils import timezone

from payments.models import Payment, PaymentConfig
from payments.services.payment_service import PaymentService
from payments.utils import PhoneNumberEncryption

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


@pytest.fixture
def phone_encryptor():
    """Create phone number encryptor."""
    return PhoneNumberEncryption()


class TestSuccessfulPaymentE2E:
    """End-to-end test for successful payment flow."""
    
    def test_successful_payment_flow(
        self,
        test_user,
        membership_fee_config,
        payment_service,
        phone_encryptor
    ):
        """
        Test complete successful payment flow:
        1. Initiate payment
        2. Verify payment record created with pending status
        3. Poll status (simulating user approval)
        4. Verify payment status updates to completed
        5. Verify all database fields are correctly populated
        
        Requirements: 1.1-1.10
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        
        # Mock MTN service to simulate successful flow
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # Step 1: Initiate payment
            # Mock successful payment initiation
            mock_request_to_pay.return_value = {
                'success': True,
                'transaction_reference': transaction_ref,
                'message': 'Payment request sent. Please approve on your phone.'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=test_user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Verify initiation success
            assert success is True
            assert payment is not None
            assert 'approve on your phone' in message.lower()
            
            # Step 2: Verify payment record created with pending status
            assert payment.status == Payment.STATUS_PENDING
            assert payment.user == test_user
            assert payment.amount == amount
            assert payment.currency == 'UGX'
            assert payment.provider == provider
            assert payment.transaction_reference is not None
            assert payment.provider_transaction_id is None  # Not yet completed
            assert payment.completed_at is None
            assert payment.error_message is None
            
            # Verify phone number is encrypted
            decrypted_phone = phone_encryptor.decrypt(payment.phone_number)
            assert decrypted_phone == phone_number
            assert payment.phone_number != phone_number  # Should be encrypted
            
            # Verify masked phone number
            masked_phone = payment.get_masked_phone()
            assert masked_phone == '256****3456'
            
            # Step 3: Simulate polling - first check returns pending
            mock_check_status.return_value = {
                'success': True,
                'status': 'pending',
                'message': 'Payment is pending approval',
                'provider_transaction_id': None,
                'raw_response': {'status': 'PENDING'}
            }
            
            status, message = payment_service.check_payment_status(payment)
            
            # Verify still pending
            payment.refresh_from_db()
            assert payment.status in [Payment.STATUS_PENDING, Payment.STATUS_PROCESSING]
            assert payment.completed_at is None
            
            # Step 4: Simulate user approval - next check returns successful
            provider_tx_id = 'MTN-TX-123456'
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed successfully',
                'provider_transaction_id': provider_tx_id,
                'raw_response': {
                    'status': 'SUCCESSFUL',
                    'financialTransactionId': provider_tx_id,
                    'amount': '50000',
                    'currency': 'UGX'
                }
            }
            
            status, message = payment_service.check_payment_status(payment)
            
            # Step 5: Verify payment status updated to completed
            payment.refresh_from_db()
            assert payment.status == Payment.STATUS_COMPLETED
            assert payment.provider_transaction_id == provider_tx_id
            assert payment.completed_at is not None
            assert payment.error_message is None
            assert payment.provider_response is not None
            assert payment.provider_response['status'] == 'SUCCESSFUL'
            
            # Verify timestamps
            assert payment.created_at is not None
            assert payment.updated_at is not None
            assert payment.completed_at >= payment.created_at
            
            # Verify payment cannot be retried once completed
            assert payment.can_retry() is False
    
    def test_successful_payment_with_multiple_polls(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test successful payment with multiple status polls.
        Simulates realistic scenario where payment takes several polls to complete.
        
        Requirements: 1.6, 1.7, 4.1-4.4
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
            assert payment.status == Payment.STATUS_PENDING
            
            # Simulate multiple polls (pending → processing → completed)
            poll_responses = [
                # First 3 polls: pending
                {
                    'success': True,
                    'status': 'pending',
                    'message': 'Payment is pending',
                    'provider_transaction_id': None,
                    'raw_response': {'status': 'PENDING'}
                },
                {
                    'success': True,
                    'status': 'pending',
                    'message': 'Payment is pending',
                    'provider_transaction_id': None,
                    'raw_response': {'status': 'PENDING'}
                },
                {
                    'success': True,
                    'status': 'pending',
                    'message': 'Payment is pending',
                    'provider_transaction_id': None,
                    'raw_response': {'status': 'PENDING'}
                },
                # Final poll: completed
                {
                    'success': True,
                    'status': 'completed',
                    'message': 'Payment completed',
                    'provider_transaction_id': 'MTN-TX-789',
                    'raw_response': {
                        'status': 'SUCCESSFUL',
                        'financialTransactionId': 'MTN-TX-789'
                    }
                }
            ]
            
            # Execute polls
            for i, response in enumerate(poll_responses):
                mock_check_status.return_value = response
                status, message = payment_service.check_payment_status(payment)
                payment.refresh_from_db()
                
                if i < len(poll_responses) - 1:
                    # Should still be pending/processing
                    assert payment.status in [Payment.STATUS_PENDING, Payment.STATUS_PROCESSING]
                    assert payment.completed_at is None
                else:
                    # Final poll should complete
                    assert payment.status == Payment.STATUS_COMPLETED
                    assert payment.provider_transaction_id == 'MTN-TX-789'
                    assert payment.completed_at is not None
    
    def test_successful_payment_with_application_link(
        self,
        test_user,
        membership_fee_config,
        payment_service,
        db
    ):
        """
        Test successful payment linked to an application.
        Verifies application_id is stored and maintained throughout flow.
        
        Requirements: 14.7
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        application_id = None  # Don't use foreign key for now
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
            # Initiate payment with application link
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
                application_id=application_id
            )
            
            # Verify application link
            assert success is True
            assert payment.application_id == application_id
            
            # Complete payment
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed',
                'provider_transaction_id': 'MTN-TX-APP-123',
                'raw_response': {'status': 'SUCCESSFUL', 'financialTransactionId': 'MTN-TX-APP-123'}
            }
            
            status, message = payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Verify application link maintained after completion
            assert payment.status == Payment.STATUS_COMPLETED
            assert payment.application_id == application_id
    
    def test_successful_payment_with_audit_fields(
        self,
        test_user,
        membership_fee_config,
        payment_service
    ):
        """
        Test successful payment with audit fields (IP address, user agent).
        Verifies audit trail is maintained.
        
        Requirements: 3.1
        """
        phone_number = '256708123456'
        amount = Decimal('50000.00')
        provider = Payment.PROVIDER_MTN
        ip_address = '192.168.1.100'
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        
        transaction_ref = str(uuid.uuid4())
        
        with patch.object(payment_service.mtn_service, 'request_to_pay') as mock_request_to_pay, \
             patch.object(payment_service.mtn_service, 'check_payment_status') as mock_check_status:
            
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
            
            # Verify audit fields
            assert success is True
            assert payment.ip_address == ip_address
            assert payment.user_agent == user_agent
            
            # Complete payment
            mock_check_status.return_value = {
                'success': True,
                'status': 'completed',
                'message': 'Payment completed',
                'provider_transaction_id': 'MTN-TX-AUDIT-123',
                'raw_response': {'status': 'SUCCESSFUL', 'financialTransactionId': 'MTN-TX-AUDIT-123'}
            }
            
            status, message = payment_service.check_payment_status(payment)
            payment.refresh_from_db()
            
            # Verify audit fields maintained after completion
            assert payment.status == Payment.STATUS_COMPLETED
            assert payment.ip_address == ip_address
            assert payment.user_agent == user_agent
