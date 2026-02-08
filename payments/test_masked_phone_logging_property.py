"""
Property-based tests for masked phone numbers in logs.

Feature: mobile-money-payment-integration
Property 17: Masked Phone Numbers in Logs

For any log entry that includes a phone number, the logged value
should be masked showing only the first 3 digits and last 4 digits
(format: 256****3456), never the complete phone number.

Validates: Requirements 7.5, 9.7
"""
import pytest
import logging
from hypothesis import given, strategies as st, settings, Phase, HealthCheck
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch, MagicMock
from payments.services.payment_service import PaymentService
from payments.models import Payment
from payments.utils import PhoneNumberEncryption

User = get_user_model()


# Strategy for generating valid phone numbers
@st.composite
def valid_phone_numbers(draw):
    """Generate valid phone numbers in format 256XXXXXXXXX."""
    digits = draw(st.text(alphabet='0123456789', min_size=9, max_size=9))
    return f"256{digits}"


@pytest.fixture
def test_user(db):
    """Create test user."""
    return User.objects.create_user(
        email='testuser@example.com',
        password='testpass123'
    )


@pytest.fixture
def mock_mtn_service():
    """Mock MTN service to avoid actual API calls."""
    with patch('payments.services.payment_service.MTNService') as mock:
        instance = mock.return_value
        instance.request_to_pay.return_value = {
            'success': True,
            'transaction_reference': 'test-ref-123',
            'message': 'Payment request sent'
        }
        instance.check_payment_status.return_value = {
            'success': True,
            'status': 'completed',
            'provider_transaction_id': 'mtn-tx-123',
            'message': 'Payment successful'
        }
        yield instance


@pytest.mark.django_db
@given(
    phone_number=valid_phone_numbers()
)
@settings(
    max_examples=20,
    phases=[Phase.generate, Phase.target],
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_phone_numbers_are_masked_in_payment_initiation_logs(
    phone_number,
    test_user,
    mock_mtn_service
):
    """
    Property 17: Masked Phone Numbers in Payment Initiation Logs
    
    For any phone number used in payment initiation, the logged value
    should be masked (256****XXXX format), never the complete phone number.
    
    Validates: Requirements 7.5, 9.7
    """
    # Create a mock logger to capture log calls
    with patch('payments.services.payment_service.logger') as mock_logger:
        # Initialize payment service
        payment_service = PaymentService()
        
        # Initiate payment
        success, payment, message = payment_service.initiate_payment(
            user=test_user,
            phone_number=phone_number,
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN,
            ip_address='192.168.1.1',
            user_agent='Test Agent'
        )
        
        # Property: Logger should have been called
        assert mock_logger.info.called or mock_logger.warning.called or mock_logger.error.called
        
        # Property: No log call should contain the full phone number
        for call in mock_logger.info.call_args_list:
            # Check both args and kwargs
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"
        
        for call in mock_logger.warning.call_args_list:
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"
        
        for call in mock_logger.error.call_args_list:
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"
        
        # Property: Logs should contain masked phone number
        # Masked format: 256****XXXX (first 3 digits + **** + last 4 digits)
        expected_masked = f"{phone_number[:3]}****{phone_number[-4:]}"
        
        # Check if masked phone appears in any log call
        found_masked = False
        for call in mock_logger.info.call_args_list:
            if 'extra' in call.kwargs and 'masked_phone' in call.kwargs['extra']:
                masked_value = call.kwargs['extra']['masked_phone']
                assert masked_value == expected_masked, \
                    f"Expected masked phone {expected_masked}, got {masked_value}"
                found_masked = True
        
        # If payment was successful, masked phone should be in logs
        if success:
            assert found_masked, "Masked phone number not found in logs"


@pytest.mark.django_db
@given(
    phone_number=valid_phone_numbers()
)
@settings(
    max_examples=20,
    phases=[Phase.generate, Phase.target],
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_phone_numbers_are_masked_in_status_check_logs(
    phone_number,
    test_user,
    mock_mtn_service
):
    """
    Property 17: Masked Phone Numbers in Status Check Logs
    
    For any phone number in payment records, status check logs
    should never contain the full phone number.
    
    Validates: Requirements 7.5, 9.7
    """
    # Create a payment record with encrypted phone
    import uuid
    encryptor = PhoneNumberEncryption()
    encrypted_phone = encryptor.encrypt(phone_number)
    
    payment = Payment.objects.create(
        user=test_user,
        phone_number=encrypted_phone,
        amount=Decimal('50000.00'),
        currency='UGX',
        provider=Payment.PROVIDER_MTN,
        transaction_reference=str(uuid.uuid4()),  # Unique reference
        status=Payment.STATUS_PENDING
    )
    
    # Create a mock logger to capture log calls
    with patch('payments.services.payment_service.logger') as mock_logger:
        # Initialize payment service
        payment_service = PaymentService()
        
        # Check payment status
        status, message = payment_service.check_payment_status(payment)
        
        # Property: No log call should contain the full phone number
        for call in mock_logger.info.call_args_list:
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"
        
        for call in mock_logger.warning.call_args_list:
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"
        
        for call in mock_logger.error.call_args_list:
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"


@pytest.mark.django_db
@given(
    phone_number=valid_phone_numbers()
)
@settings(
    max_examples=20,
    phases=[Phase.generate, Phase.target],
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_phone_numbers_are_masked_in_retry_logs(
    phone_number,
    test_user,
    mock_mtn_service
):
    """
    Property 17: Masked Phone Numbers in Retry Logs
    
    For any phone number in payment retry operations, logs
    should never contain the full phone number.
    
    Validates: Requirements 7.5, 9.7
    """
    # Create a failed payment record with encrypted phone
    import uuid
    encryptor = PhoneNumberEncryption()
    encrypted_phone = encryptor.encrypt(phone_number)
    
    payment = Payment.objects.create(
        user=test_user,
        phone_number=encrypted_phone,
        amount=Decimal('50000.00'),
        currency='UGX',
        provider=Payment.PROVIDER_MTN,
        transaction_reference=str(uuid.uuid4()),  # Unique reference
        status=Payment.STATUS_FAILED,
        error_message='Payment failed'
    )
    
    # Create a mock logger to capture log calls
    with patch('payments.services.payment_service.logger') as mock_logger:
        # Initialize payment service
        payment_service = PaymentService()
        
        # Retry payment
        success, new_payment, message = payment_service.retry_payment(payment)
        
        # Property: No log call should contain the full phone number
        for call in mock_logger.info.call_args_list:
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"
        
        for call in mock_logger.warning.call_args_list:
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"
        
        for call in mock_logger.error.call_args_list:
            call_str = str(call)
            assert phone_number not in call_str, \
                f"Full phone number {phone_number} found in log call: {call_str}"


@pytest.mark.django_db
def test_masked_phone_format_is_correct():
    """
    Property 17: Masked Phone Number Format
    
    The mask() function should always return phone numbers in the format
    256****XXXX (first 3 digits + **** + last 4 digits).
    
    Validates: Requirements 7.5, 9.7
    """
    encryptor = PhoneNumberEncryption()
    
    # Test with various phone numbers
    test_cases = [
        ('256701234567', '256****4567'),
        ('256781234567', '256****4567'),
        ('256791234567', '256****4567'),
        ('256700000000', '256****0000'),
        ('256799999999', '256****9999'),
    ]
    
    for phone, expected_masked in test_cases:
        masked = encryptor.mask(phone)
        assert masked == expected_masked, \
            f"Expected {expected_masked}, got {masked} for phone {phone}"
        
        # Property: Masked phone should not contain the middle digits
        middle_digits = phone[3:-4]
        assert middle_digits not in masked, \
            f"Middle digits {middle_digits} found in masked phone {masked}"
        
        # Property: Masked phone should contain first 3 and last 4 digits
        assert masked.startswith(phone[:3]), \
            f"Masked phone {masked} should start with {phone[:3]}"
        assert masked.endswith(phone[-4:]), \
            f"Masked phone {masked} should end with {phone[-4:]}"
        
        # Property: Masked phone should contain exactly 4 asterisks
        assert masked.count('*') == 4, \
            f"Masked phone {masked} should contain exactly 4 asterisks"


@pytest.mark.django_db
@given(
    phone_number=valid_phone_numbers()
)
@settings(
    max_examples=20,
    phases=[Phase.generate, Phase.target],
    deadline=None
)
def test_masked_phone_never_reveals_full_number(phone_number):
    """
    Property 17: Masked Phone Never Reveals Full Number
    
    For any valid phone number, the masked version should never
    reveal the complete phone number.
    
    Validates: Requirements 7.5, 9.7
    """
    encryptor = PhoneNumberEncryption()
    masked = encryptor.mask(phone_number)
    
    # Property: Masked phone should not equal the original phone
    assert masked != phone_number, \
        f"Masked phone {masked} should not equal original {phone_number}"
    
    # Property: Masked phone should be 11 characters (256****XXXX)
    # 3 (prefix) + 4 (asterisks) + 4 (last digits) = 11
    assert len(masked) == 11, \
        f"Masked phone length {len(masked)} should be 11 characters"
    
    # Property: Middle digits should not be visible
    middle_digits = phone_number[3:-4]
    assert middle_digits not in masked, \
        f"Middle digits {middle_digits} should not be visible in masked phone {masked}"
    
    # Property: Masked phone should contain asterisks
    assert '*' in masked, \
        f"Masked phone {masked} should contain asterisks"
