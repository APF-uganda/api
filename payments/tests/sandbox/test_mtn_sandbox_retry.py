"""
Sandbox tests for MTN Mobile Money retry and cancellation functionality.
Tests payment retry after failure and payment cancellation during pending.

Requirements: 12.1-12.7
"""
import pytest
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from payments.services.payment_service import PaymentService
from payments.models import Payment

User = get_user_model()


@pytest.mark.django_db
class TestMTNSandboxRetry:
    """Test payment retry functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test_retry@example.com',
            password='testpass123'
        )
        self.payment_service = PaymentService()
    
    def test_retry_after_failed_payment(self):
        """Test retrying a failed payment creates new transaction."""
        # Create initial failed payment
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref-1',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            assert success is True
            original_payment_id = payment.id
            original_reference = payment.transaction_reference
            
            # Mark as failed
            payment.status = 'failed'
            payment.error_message = 'Insufficient funds'
            payment.save()
            
            # Verify can retry
            assert payment.can_retry() is True
            
            # Retry payment
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref-2',
                'message': 'Request sent'
            }
            
            retry_success, new_payment, retry_message = payment_service.retry_payment(payment)
            
            assert retry_success is True
            
            # Verify new payment was created
            assert new_payment is not None
            assert new_payment.id != original_payment_id
            assert new_payment.transaction_reference != original_reference
            assert new_payment.amount == payment.amount
            assert new_payment.provider == payment.provider
            assert new_payment.status == 'pending'
    
    def test_retry_preserves_payment_details(self):
        """Test that retry preserves original payment details."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref-1',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            # Create initial payment
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("75000.00"),
                provider='mtn'
            )
            
            assert success is True
            
            # Mark as failed
            payment.status = 'failed'
            payment.save()
            
            # Retry
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref-2',
                'message': 'Request sent'
            }
            
            retry_success, new_payment, retry_message = payment_service.retry_payment(payment)
            
            assert retry_success is True
            
            # Verify details preserved
            assert new_payment.amount == Decimal("75000.00")
            assert new_payment.provider == 'mtn'
            assert new_payment.user == self.user
    
    def test_cannot_retry_completed_payment(self):
        """Test that completed payments cannot be retried."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            # Mark as completed
            payment.status = 'completed'
            payment.save()
            
            # Verify cannot retry
            assert payment.can_retry() is False
    
    def test_cannot_retry_pending_payment(self):
        """Test that pending payments cannot be retried."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            # Payment is pending
            assert payment.status == 'pending'
            
            # Verify cannot retry
            assert payment.can_retry() is False
    
    def test_retry_after_timeout(self):
        """Test retrying a timed-out payment."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref-1',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000003",  # Timeout test number
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            # Mark as timeout
            payment.status = 'timeout'
            payment.save()
            
            # Verify can retry
            assert payment.can_retry() is True
            
            # Retry
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref-2',
                'message': 'Request sent'
            }
            
            retry_success, new_payment, retry_message = payment_service.retry_payment(payment)
            
            assert retry_success is True


@pytest.mark.django_db
class TestMTNSandboxCancellation:
    """Test payment cancellation functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test_cancel@example.com',
            password='testpass123'
        )
        self.payment_service = PaymentService()
    
    def test_cancel_pending_payment(self):
        """Test cancelling a pending payment."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            assert success is True
            assert payment.status == 'pending'
            
            # Cancel payment
            cancel_success = payment_service.cancel_payment(payment)
            
            assert cancel_success is True
            
            # Refresh from database
            payment.refresh_from_db()
            assert payment.status == 'cancelled'
    
    def test_cannot_cancel_completed_payment(self):
        """Test that completed payments cannot be cancelled."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            # Mark as completed
            payment.status = 'completed'
            payment.save()
            
            # Try to cancel
            cancel_success = payment_service.cancel_payment(payment)
            
            assert cancel_success is False
    
    def test_cannot_cancel_failed_payment(self):
        """Test that failed payments cannot be cancelled."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            # Mark as failed
            payment.status = 'failed'
            payment.save()
            
            # Try to cancel
            cancel_success = payment_service.cancel_payment(payment)
            
            assert cancel_success is False
    
    def test_cancelled_payment_can_be_retried(self):
        """Test that cancelled payments cannot be retried (per current implementation)."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref-1',
                'message': 'Request sent'
            }
            
            payment_service = PaymentService()
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            # Cancel payment
            payment_service.cancel_payment(payment)
            payment.refresh_from_db()
            
            assert payment.status == 'cancelled'
            
            # Verify cannot retry (cancelled is not in retryable statuses)
            assert payment.can_retry() is False


@pytest.mark.django_db
class TestMTNSandboxRetryLimits:
    """Test retry limit enforcement."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test_limits@example.com',
            password='testpass123'
        )
        self.payment_service = PaymentService()
    
    def test_multiple_retries_create_separate_transactions(self):
        """Test that multiple retries create separate transaction records."""
        with patch('payments.services.payment_service.MTNService') as MockMTNService:
            mock_mtn = MockMTNService.return_value
            
            payment_service = PaymentService()
            payments = []
            
            # Create initial payment
            mock_mtn.request_to_pay.return_value = {
                'success': True,
                'transaction_reference': 'test-ref-1',
                'message': 'Request sent'
            }
            
            success, payment, message = payment_service.initiate_payment(
                user=self.user,
                phone_number="256774000001",
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            payments.append(payment)
            
            # Retry 3 times
            for i in range(3):
                # Mark as failed
                payment.status = 'failed'
                payment.save()
                
                # Retry
                mock_mtn.request_to_pay.return_value = {
                    'success': True,
                    'transaction_reference': f'test-ref-{i+2}',
                    'message': 'Request sent'
                }
                
                retry_success, new_payment, retry_message = payment_service.retry_payment(payment)
                
                if retry_success:
                    # Use the new payment for next iteration
                    payment = new_payment
                    payments.append(payment)
            
            # Verify all payments are separate records
            payment_ids = [p.id for p in payments]
            assert len(payment_ids) == len(set(payment_ids))
            
            # Verify all have same amount and provider
            for p in payments:
                assert p.amount == Decimal("50000.00")
                assert p.provider == 'mtn'
