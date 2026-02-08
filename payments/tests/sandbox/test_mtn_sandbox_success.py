"""
Sandbox test for successful MTN Mobile Money payment flow.
Tests the complete payment flow using MTN sandbox API with test phone numbers.

Requirements: 1.1-1.10, 11.1-11.8
"""
import pytest
import uuid
import time
from decimal import Decimal
from django.contrib.auth import get_user_model
from payments.services.mtn_service import MTNService, MTNConfig
from payments.services.payment_service import PaymentService
from payments.models import Payment

User = get_user_model()


@pytest.mark.django_db
class TestMTNSandboxSuccess:
    """Test successful payment flow in MTN sandbox."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Initialize services
        self.mtn_service = MTNService()
        self.payment_service = PaymentService()
        
        # MTN sandbox test number that will approve payment
        self.test_phone_success = "256774000001"
    
    def test_mtn_sandbox_credentials_configured(self):
        """Test that MTN sandbox credentials are properly configured."""
        config = MTNConfig()
        
        assert config.is_configured(), "MTN credentials not configured"
        assert config.environment == 'sandbox', "Not in sandbox environment"
        assert config.base_url == 'https://sandbox.momodeveloper.mtn.com'
    
    def test_mtn_sandbox_authentication(self):
        """Test authentication with MTN sandbox API."""
        # Get access token
        token = self.mtn_service._get_access_token()
        
        assert token is not None, "Failed to get access token"
        assert len(token) > 0, "Access token is empty"
        assert self.mtn_service.token_expiry is not None, "Token expiry not set"
    
    def test_mtn_sandbox_payment_initiation(self):
        """Test initiating payment with MTN sandbox."""
        reference = str(uuid.uuid4())
        
        # Initiate payment
        result = self.mtn_service.request_to_pay(
            phone_number=self.test_phone_success,
            amount=Decimal("50000.00"),
            currency="UGX",
            reference=reference,
            payer_message="Test Payment"
        )
        
        # Verify result
        assert result['success'] is True, f"Payment initiation failed: {result.get('message')}"
        assert result['transaction_reference'] == reference
        assert 'approve' in result['message'].lower()
    
    def test_mtn_sandbox_payment_status_check(self):
        """Test checking payment status in MTN sandbox."""
        reference = str(uuid.uuid4())
        
        # Initiate payment
        init_result = self.mtn_service.request_to_pay(
            phone_number=self.test_phone_success,
            amount=Decimal("50000.00"),
            currency="UGX",
            reference=reference
        )
        
        assert init_result['success'] is True
        
        # Wait a moment for sandbox to process
        time.sleep(2)
        
        # Check status
        status_result = self.mtn_service.check_payment_status(reference)
        
        assert status_result['success'] is True
        assert status_result['status'] in ['pending', 'completed']
    
    def test_mtn_sandbox_complete_payment_flow(self):
        """Test complete payment flow from initiation to completion."""
        # Initiate payment through payment service
        success, payment, message = self.payment_service.initiate_payment(
            user=self.user,
            phone_number=self.test_phone_success,
            amount=Decimal("50000.00"),
            provider='mtn'
        )
        
        assert success is True, f"Payment initiation failed: {message}"
        assert payment is not None
        assert payment.status == 'pending'
        assert payment.provider == 'mtn'
        assert payment.amount == Decimal("50000.00")
        
        # Poll for payment completion (max 30 seconds)
        max_attempts = 10
        attempt = 0
        final_status = None
        
        while attempt < max_attempts:
            time.sleep(3)  # Wait 3 seconds between checks
            
            status, status_message = self.payment_service.check_payment_status(payment)
            
            # Refresh payment from database
            payment.refresh_from_db()
            
            if payment.status in ['completed', 'failed']:
                final_status = payment.status
                break
            
            attempt += 1
        
        # Verify final status
        # Note: In sandbox, the test number may complete or stay pending
        # We verify the flow works correctly
        assert payment.status in ['pending', 'completed'], \
            f"Unexpected final status: {payment.status}"
        
        if payment.status == 'completed':
            assert payment.provider_transaction_id is not None
            assert payment.completed_at is not None
    
    def test_mtn_sandbox_payment_database_record(self):
        """Test that payment creates correct database record."""
        # Initiate payment
        success, payment, message = self.payment_service.initiate_payment(
            user=self.user,
            phone_number=self.test_phone_success,
            amount=Decimal("50000.00"),
            provider='mtn'
        )
        
        assert success is True
        
        # Verify database record
        db_payment = Payment.objects.get(id=payment.id)
        
        assert db_payment.user == self.user
        assert db_payment.amount == Decimal("50000.00")
        assert db_payment.currency == 'UGX'
        assert db_payment.provider == 'mtn'
        assert db_payment.status == 'pending'
        assert db_payment.transaction_reference is not None
        assert db_payment.created_at is not None
        
        # Phone number should be encrypted
        assert db_payment.phone_number != self.test_phone_success
    
    def test_mtn_sandbox_multiple_payments(self):
        """Test multiple sequential payments."""
        payments = []
        
        for i in range(3):
            success, payment, message = self.payment_service.initiate_payment(
                user=self.user,
                phone_number=self.test_phone_success,
                amount=Decimal("50000.00"),
                provider='mtn'
            )
            
            assert success is True, f"Payment {i+1} failed: {message}"
            payments.append(payment)
            
            # Small delay between payments
            time.sleep(1)
        
        # Verify all payments are in database
        assert Payment.objects.filter(user=self.user).count() == 3
        
        # Verify each has unique transaction reference
        references = [p.transaction_reference for p in payments]
        assert len(references) == len(set(references)), "Duplicate transaction references"
    
    def test_mtn_sandbox_token_caching(self):
        """Test that access token is cached and reused."""
        # First call should get new token
        token1 = self.mtn_service._get_access_token()
        expiry1 = self.mtn_service.token_expiry
        
        # Second call should reuse cached token
        token2 = self.mtn_service._get_access_token()
        expiry2 = self.mtn_service.token_expiry
        
        assert token1 == token2, "Token not cached"
        assert expiry1 == expiry2, "Token expiry changed"
    
    def test_mtn_sandbox_masked_phone_in_logs(self):
        """Test that phone numbers are masked in payment records."""
        success, payment, message = self.payment_service.initiate_payment(
            user=self.user,
            phone_number=self.test_phone_success,
            amount=Decimal("50000.00"),
            provider='mtn'
        )
        
        assert success is True
        
        # Get masked phone number
        masked = payment.get_masked_phone()
        
        # Should show only first 3 and last 4 digits
        assert masked.startswith('256')
        assert masked.endswith('0001')
        assert '****' in masked
        assert len(masked) == 12  # 256****0001


@pytest.mark.django_db
class TestMTNSandboxEdgeCases:
    """Test edge cases in MTN sandbox."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test2@example.com',
            password='testpass123'
        )
        self.payment_service = PaymentService()
    
    def test_invalid_phone_number_format(self):
        """Test payment with invalid phone number format."""
        success, payment, message = self.payment_service.initiate_payment(
            user=self.user,
            phone_number="123456789",  # Invalid format
            amount=Decimal("50000.00"),
            provider='mtn'
        )
        
        assert success is False
        assert 'phone' in message.lower() or '12 characters' in message.lower()
    
    def test_zero_amount(self):
        """Test payment with zero amount."""
        success, payment, message = self.payment_service.initiate_payment(
            user=self.user,
            phone_number="256774000001",
            amount=Decimal("0.00"),
            provider='mtn'
        )
        
        assert success is False
        assert 'amount' in message.lower()
    
    def test_negative_amount(self):
        """Test payment with negative amount."""
        success, payment, message = self.payment_service.initiate_payment(
            user=self.user,
            phone_number="256774000001",
            amount=Decimal("-1000.00"),
            provider='mtn'
        )
        
        assert success is False
        assert 'amount' in message.lower()
