"""
Property-based tests for payment initiation.

Feature: mobile-money-payment-integration
Property 2: Payment Initiation Creates Database Record

For any valid payment initiation request (with valid phone number, amount, and 
provider), the system should create exactly one Payment_Transaction record in 
the database with status "pending" and all required fields populated 
(transaction_reference, phone_number, amount, currency, provider, user_id, 
created_at).

Validates: Requirements 1.4, 2.4, 3.1
"""
import pytest
import os
from decimal import Decimal
from hypothesis import given, strategies as st, settings
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from payments.models import Payment
from payments.services.payment_service import PaymentService
from payments.utils import PhoneNumberEncryption

User = get_user_model()

# Set dummy MTN credentials for testing if not set
os.environ.setdefault('MTN_API_USER', 'test-api-user')
os.environ.setdefault('MTN_API_KEY', 'test-api-key')
os.environ.setdefault('MTN_SUBSCRIPTION_KEY', 'test-subscription-key')


# Strategy for generating valid phone numbers (256 + 9 digits)
valid_phone_numbers = st.builds(
    lambda digits: f"256{digits}",
    digits=st.text(alphabet='0123456789', min_size=9, max_size=9)
)

# Strategy for generating valid payment amounts (positive decimals)
valid_amounts = st.decimals(
    min_value=Decimal('1.00'),
    max_value=Decimal('10000000.00'),
    places=2
)

# Strategy for generating provider choices
valid_providers = st.sampled_from([Payment.PROVIDER_MTN])  # Only MTN for Phase 1


@pytest.mark.django_db
class TestPaymentInitiationProperties:
    """Property-based tests for payment initiation."""
    
    @given(
        phone_number=valid_phone_numbers,
        amount=valid_amounts,
        provider=valid_providers
    )
    @settings(max_examples=20)
    def test_payment_initiation_creates_database_record(
        self, 
        phone_number, 
        amount, 
        provider
    ):
        """
        Property: Payment initiation creates exactly one database record.
        
        For any valid payment initiation request (valid phone, amount, provider),
        the system should create exactly one Payment record with status='pending'
        and all required fields populated.
        """
        # Setup: Create a test user
        user = User.objects.create_user(
            email=f'test_{phone_number[-4:]}@example.com',
            password='testpass123'
        )
        
        # Mock the provider service to avoid actual API calls
        with patch.object(PaymentService, '_get_provider_service') as mock_provider:
            mock_service = MagicMock()
            mock_service.request_to_pay.return_value = {
                'success': True,
                'message': 'Payment request sent'
            }
            mock_provider.return_value = mock_service
            
            # Get initial payment count
            initial_count = Payment.objects.count()
            
            # Execute: Initiate payment
            service = PaymentService()
            success, payment, message = service.initiate_payment(
                user=user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Verify: Exactly one new payment record created
            final_count = Payment.objects.count()
            assert final_count == initial_count + 1, \
                f"Expected exactly one new payment record, got {final_count - initial_count}"
            
            # Verify: Payment initiation succeeded
            assert success is True, \
                f"Payment initiation should succeed for valid inputs"
            assert payment is not None, \
                "Payment object should be returned"
            assert isinstance(payment, Payment), \
                f"Returned object should be Payment instance, got {type(payment)}"
            
            # Verify: Payment has correct status
            assert payment.status == Payment.STATUS_PENDING, \
                f"Payment status should be 'pending', got '{payment.status}'"
            
            # Verify: All required fields are populated
            assert payment.transaction_reference is not None, \
                "Transaction reference should be populated"
            assert payment.transaction_reference != '', \
                "Transaction reference should not be empty"
            
            assert payment.phone_number is not None, \
                "Phone number should be populated"
            assert payment.phone_number != '', \
                "Phone number should not be empty"
            
            # Verify: Phone number is encrypted (different from plaintext)
            assert payment.phone_number != phone_number, \
                "Phone number should be encrypted in database"
            
            # Verify: Phone number can be decrypted back to original
            encryptor = PhoneNumberEncryption()
            decrypted_phone = encryptor.decrypt(payment.phone_number)
            assert decrypted_phone == phone_number, \
                f"Decrypted phone should match original: {decrypted_phone} != {phone_number}"
            
            assert payment.amount == amount, \
                f"Payment amount should be {amount}, got {payment.amount}"
            
            assert payment.currency == 'UGX', \
                f"Payment currency should be 'UGX', got '{payment.currency}'"
            
            assert payment.provider == provider, \
                f"Payment provider should be '{provider}', got '{payment.provider}'"
            
            assert payment.user == user, \
                "Payment should be linked to the correct user"
            
            assert payment.created_at is not None, \
                "Created timestamp should be populated"
            
            # Verify: Provider service was called with correct parameters
            mock_service.request_to_pay.assert_called_once()
            call_args = mock_service.request_to_pay.call_args
            assert call_args.kwargs['phone_number'] == phone_number, \
                "Provider should be called with correct phone number"
            assert call_args.kwargs['amount'] == amount, \
                "Provider should be called with correct amount"
            assert call_args.kwargs['currency'] == 'UGX', \
                "Provider should be called with UGX currency"
            
            # Cleanup
            user.delete()
    
    @given(
        phone_number=valid_phone_numbers,
        amount=valid_amounts,
        provider=valid_providers
    )
    @settings(max_examples=20)
    def test_failed_provider_call_still_creates_record(
        self, 
        phone_number, 
        amount, 
        provider
    ):
        """
        Property: Payment record is created even if provider call fails.
        
        When the provider service returns an error, a Payment record should
        still be created with status='failed' and error message populated.
        """
        # Setup: Create a test user
        user = User.objects.create_user(
            email=f'test_{phone_number[-4:]}@example.com',
            password='testpass123'
        )
        
        # Mock the provider service to return failure
        with patch.object(PaymentService, '_get_provider_service') as mock_provider:
            mock_service = MagicMock()
            mock_service.request_to_pay.return_value = {
                'success': False,
                'message': 'Insufficient funds'
            }
            mock_provider.return_value = mock_service
            
            # Get initial payment count
            initial_count = Payment.objects.count()
            
            # Execute: Initiate payment
            service = PaymentService()
            success, payment, message = service.initiate_payment(
                user=user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Verify: Payment record was created
            final_count = Payment.objects.count()
            assert final_count == initial_count + 1, \
                "Payment record should be created even when provider fails"
            
            # Verify: Payment initiation failed
            assert success is False, \
                "Payment initiation should fail when provider returns error"
            assert payment is not None, \
                "Payment object should still be returned"
            
            # Verify: Payment has failed status
            assert payment.status == Payment.STATUS_FAILED, \
                f"Payment status should be 'failed', got '{payment.status}'"
            
            # Verify: Error message is populated
            assert payment.error_message is not None, \
                "Error message should be populated"
            assert payment.error_message != '', \
                "Error message should not be empty"
            
            # Cleanup
            user.delete()
    
    @given(
        phone_number=valid_phone_numbers,
        amount=valid_amounts,
        provider=valid_providers
    )
    @settings(max_examples=20)
    def test_transaction_reference_is_unique(
        self, 
        phone_number, 
        amount, 
        provider
    ):
        """
        Property: Each payment has a unique transaction reference.
        
        For any two payment initiation requests, the transaction references
        should be different (unique).
        """
        # Setup: Create a test user
        user = User.objects.create_user(
            email=f'test_{phone_number[-4:]}@example.com',
            password='testpass123'
        )
        
        # Mock the provider service
        with patch.object(PaymentService, '_get_provider_service') as mock_provider:
            mock_service = MagicMock()
            mock_service.request_to_pay.return_value = {
                'success': True,
                'message': 'Payment request sent'
            }
            mock_provider.return_value = mock_service
            
            # Execute: Create two payments
            service = PaymentService()
            
            success1, payment1, _ = service.initiate_payment(
                user=user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            success2, payment2, _ = service.initiate_payment(
                user=user,
                phone_number=phone_number,
                amount=amount,
                provider=provider
            )
            
            # Verify: Both payments created successfully
            assert success1 is True and success2 is True, \
                "Both payments should be created successfully"
            
            # Verify: Transaction references are unique
            assert payment1.transaction_reference != payment2.transaction_reference, \
                "Transaction references should be unique for different payments"
            
            # Cleanup
            user.delete()
    
    @given(
        phone_number=valid_phone_numbers,
        amount=valid_amounts,
        provider=valid_providers
    )
    @settings(max_examples=20)
    def test_payment_with_application_id_links_correctly(
        self, 
        phone_number, 
        amount, 
        provider
    ):
        """
        Property: Payment with application_id links to application.
        
        When an application_id is provided, the Payment record should
        store this link correctly.
        """
        # Setup: Create a test user
        user = User.objects.create_user(
            email=f'test_{phone_number[-4:]}@example.com',
            password='testpass123'
        )
        
        # Mock the provider service
        with patch.object(PaymentService, '_get_provider_service') as mock_provider:
            mock_service = MagicMock()
            mock_service.request_to_pay.return_value = {
                'success': True,
                'message': 'Payment request sent'
            }
            mock_provider.return_value = mock_service
            
            # Execute: Initiate payment with application_id
            service = PaymentService()
            application_id = 12345  # Mock application ID
            
            success, payment, message = service.initiate_payment(
                user=user,
                phone_number=phone_number,
                amount=amount,
                provider=provider,
                application_id=application_id
            )
            
            # Verify: Payment created successfully
            assert success is True, \
                "Payment initiation should succeed"
            
            # Verify: Application ID is stored
            assert payment.application_id == application_id, \
                f"Application ID should be {application_id}, got {payment.application_id}"
            
            # Cleanup
            user.delete()
    
    @given(
        phone_number=valid_phone_numbers,
        amount=valid_amounts,
        provider=valid_providers
    )
    @settings(max_examples=20)
    def test_payment_with_audit_fields_stores_correctly(
        self, 
        phone_number, 
        amount, 
        provider
    ):
        """
        Property: Payment with audit fields (IP, user agent) stores correctly.
        
        When IP address and user agent are provided, they should be stored
        in the Payment record for audit purposes.
        """
        # Setup: Create a test user
        user = User.objects.create_user(
            email=f'test_{phone_number[-4:]}@example.com',
            password='testpass123'
        )
        
        # Mock the provider service
        with patch.object(PaymentService, '_get_provider_service') as mock_provider:
            mock_service = MagicMock()
            mock_service.request_to_pay.return_value = {
                'success': True,
                'message': 'Payment request sent'
            }
            mock_provider.return_value = mock_service
            
            # Execute: Initiate payment with audit fields
            service = PaymentService()
            ip_address = '192.168.1.100'
            user_agent = 'Mozilla/5.0 Test Browser'
            
            success, payment, message = service.initiate_payment(
                user=user,
                phone_number=phone_number,
                amount=amount,
                provider=provider,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Verify: Payment created successfully
            assert success is True, \
                "Payment initiation should succeed"
            
            # Verify: Audit fields are stored
            assert payment.ip_address == ip_address, \
                f"IP address should be {ip_address}, got {payment.ip_address}"
            assert payment.user_agent == user_agent, \
                f"User agent should be {user_agent}, got {payment.user_agent}"
            
            # Cleanup
            user.delete()
    
    def test_invalid_phone_number_does_not_create_record(self):
        """
        Property: Invalid phone number should not create Payment record.
        
        When phone number validation fails, no Payment record should be created.
        """
        # Setup: Create a test user
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Get initial payment count
        initial_count = Payment.objects.count()
        
        # Execute: Try to initiate payment with invalid phone
        service = PaymentService()
        success, payment, message = service.initiate_payment(
            user=user,
            phone_number='invalid',  # Invalid phone number
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN
        )
        
        # Verify: No payment record created
        final_count = Payment.objects.count()
        assert final_count == initial_count, \
            "No payment record should be created for invalid phone number"
        
        # Verify: Payment initiation failed
        assert success is False, \
            "Payment initiation should fail for invalid phone number"
        assert payment is None, \
            "Payment object should be None for invalid phone number"
        assert 'phone number' in message.lower(), \
            "Error message should mention phone number"
        
        # Cleanup
        user.delete()
    
    def test_zero_amount_does_not_create_record(self):
        """
        Property: Zero or negative amount should not create Payment record.
        
        When amount validation fails, no Payment record should be created.
        """
        # Setup: Create a test user
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Get initial payment count
        initial_count = Payment.objects.count()
        
        # Execute: Try to initiate payment with zero amount
        service = PaymentService()
        success, payment, message = service.initiate_payment(
            user=user,
            phone_number='256708123456',
            amount=Decimal('0.00'),  # Invalid amount
            provider=Payment.PROVIDER_MTN
        )
        
        # Verify: No payment record created
        final_count = Payment.objects.count()
        assert final_count == initial_count, \
            "No payment record should be created for zero amount"
        
        # Verify: Payment initiation failed
        assert success is False, \
            "Payment initiation should fail for zero amount"
        assert payment is None, \
            "Payment object should be None for zero amount"
        assert 'amount' in message.lower(), \
            "Error message should mention amount"
        
        # Cleanup
        user.delete()
