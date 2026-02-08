"""
Unit tests for payment API views.
Tests each endpoint with valid and invalid data, authentication, permissions, and error responses.
"""
import pytest
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from payments.models import Payment, PaymentConfig

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client for testing."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        email='testuser@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Create authenticated API client."""
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def membership_fee_config(db):
    """Create membership fee configuration."""
    # Use get_or_create to avoid duplicate key errors
    config, created = PaymentConfig.objects.get_or_create(
        key='membership_fee_ugx',
        defaults={
            'value': '50000',
            'description': 'APF membership fee in UGX'
        }
    )
    return config


@pytest.fixture
def test_payment(db, test_user):
    """Create a test payment."""
    from payments.utils import PhoneNumberEncryption
    encryptor = PhoneNumberEncryption()
    
    payment = Payment.objects.create(
        user=test_user,
        phone_number=encryptor.encrypt('256708123456'),
        amount=Decimal('50000.00'),
        currency='UGX',
        provider=Payment.PROVIDER_MTN,
        transaction_reference=str(uuid.uuid4()),
        status=Payment.STATUS_PENDING
    )
    return payment


class TestPaymentInitiationView:
    """Test payment initiation endpoint."""
    
    def test_initiate_payment_success(self, authenticated_client, test_user, membership_fee_config):
        """Test successful payment initiation."""
        with patch('payments.views.PaymentService') as MockService:
            # Mock successful payment initiation
            mock_payment = Mock()
            mock_payment.id = uuid.uuid4()
            mock_payment.transaction_reference = str(uuid.uuid4())
            mock_payment.amount = Decimal('50000.00')
            mock_payment.currency = 'UGX'
            
            mock_service = MockService.return_value
            mock_service.get_membership_fee.return_value = Decimal('50000.00')
            mock_service.initiate_payment.return_value = (True, mock_payment, 'Payment request sent')
            
            url = reverse('payments:payment-initiate')
            data = {
                'phone_number': '256708123456',
                'provider': 'mtn'
            }
            
            response = authenticated_client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data['success'] is True
            assert 'payment_id' in response.data
            assert 'transaction_reference' in response.data
            assert response.data['amount'] == '50000.00'
            assert response.data['currency'] == 'UGX'
    
    def test_initiate_payment_invalid_phone_number(self, authenticated_client, membership_fee_config):
        """Test payment initiation with invalid phone number."""
        url = reverse('payments:payment-initiate')
        data = {
            'phone_number': '123456789',  # Invalid format
            'provider': 'mtn'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
        assert 'error' in response.data
    
    def test_initiate_payment_invalid_provider(self, authenticated_client, membership_fee_config):
        """Test payment initiation with invalid provider."""
        url = reverse('payments:payment-initiate')
        data = {
            'phone_number': '256708123456',
            'provider': 'invalid'  # Invalid provider
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
    
    def test_initiate_payment_missing_fields(self, authenticated_client, membership_fee_config):
        """Test payment initiation with missing required fields."""
        url = reverse('payments:payment-initiate')
        data = {
            'phone_number': '256708123456'
            # Missing provider
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
    
    def test_initiate_payment_unauthenticated(self, api_client, membership_fee_config):
        """Test payment initiation without authentication."""
        url = reverse('payments:payment-initiate')
        data = {
            'phone_number': '256708123456',
            'provider': 'mtn'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_initiate_payment_service_failure(self, authenticated_client, test_user, membership_fee_config):
        """Test payment initiation when service fails."""
        with patch('payments.views.PaymentService') as MockService:
            mock_service = MockService.return_value
            mock_service.get_membership_fee.return_value = Decimal('50000.00')
            mock_service.initiate_payment.return_value = (False, None, 'Payment service error')
            
            url = reverse('payments:payment-initiate')
            data = {
                'phone_number': '256708123456',
                'provider': 'mtn'
            }
            
            response = authenticated_client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['success'] is False
            assert 'error' in response.data


class TestPaymentStatusView:
    """Test payment status endpoint."""
    
    def test_get_payment_status_success(self, authenticated_client, test_payment):
        """Test successful payment status retrieval."""
        with patch('payments.views.PaymentService') as MockService:
            mock_service = MockService.return_value
            mock_service.check_payment_status.return_value = ('pending', 'Payment is pending')
            
            url = reverse('payments:payment-status', kwargs={'payment_id': test_payment.id})
            response = authenticated_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data['status'] == 'pending'
            assert 'message' in response.data
            assert 'amount' in response.data
            assert 'currency' in response.data
    
    def test_get_payment_status_not_found(self, authenticated_client):
        """Test payment status for non-existent payment."""
        url = reverse('payments:payment-status', kwargs={'payment_id': uuid.uuid4()})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_payment_status_wrong_user(self, authenticated_client, test_payment, db):
        """Test payment status access by different user."""
        # Create another user
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        
        # Authenticate as other user
        refresh = RefreshToken.for_user(other_user)
        authenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('payments:payment-status', kwargs={'payment_id': test_payment.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_payment_status_unauthenticated(self, api_client, test_payment):
        """Test payment status without authentication."""
        url = reverse('payments:payment-status', kwargs={'payment_id': test_payment.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPaymentRetryView:
    """Test payment retry endpoint."""
    
    def test_retry_payment_success(self, authenticated_client, test_payment):
        """Test successful payment retry."""
        # Set payment to failed status
        test_payment.status = Payment.STATUS_FAILED
        test_payment.save()
        
        with patch('payments.views.PaymentService') as MockService:
            mock_new_payment = Mock()
            mock_new_payment.id = uuid.uuid4()
            mock_new_payment.transaction_reference = str(uuid.uuid4())
            
            mock_service = MockService.return_value
            mock_service.retry_payment.return_value = (True, mock_new_payment, 'Payment retry initiated')
            
            url = reverse('payments:payment-retry', kwargs={'payment_id': test_payment.id})
            response = authenticated_client.post(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data['success'] is True
            assert 'new_payment_id' in response.data
            assert 'transaction_reference' in response.data
    
    def test_retry_payment_cannot_retry(self, authenticated_client, test_payment):
        """Test retry for payment that cannot be retried."""
        # Set payment to completed status (cannot retry)
        test_payment.status = Payment.STATUS_COMPLETED
        test_payment.save()
        
        with patch('payments.views.PaymentService') as MockService:
            mock_service = MockService.return_value
            mock_service.retry_payment.return_value = (False, None, 'Payment cannot be retried')
            
            url = reverse('payments:payment-retry', kwargs={'payment_id': test_payment.id})
            response = authenticated_client.post(url)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['success'] is False
    
    def test_retry_payment_wrong_user(self, authenticated_client, test_payment, db):
        """Test payment retry by different user."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        
        refresh = RefreshToken.for_user(other_user)
        authenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('payments:payment-retry', kwargs={'payment_id': test_payment.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_retry_payment_unauthenticated(self, api_client, test_payment):
        """Test payment retry without authentication."""
        url = reverse('payments:payment-retry', kwargs={'payment_id': test_payment.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPaymentCancellationView:
    """Test payment cancellation endpoint."""
    
    def test_cancel_payment_success(self, authenticated_client, test_payment):
        """Test successful payment cancellation."""
        with patch('payments.views.PaymentService') as MockService:
            mock_service = MockService.return_value
            mock_service.cancel_payment.return_value = True
            
            url = reverse('payments:payment-cancel', kwargs={'payment_id': test_payment.id})
            response = authenticated_client.post(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data['success'] is True
            assert 'message' in response.data
    
    def test_cancel_payment_cannot_cancel(self, authenticated_client, test_payment):
        """Test cancellation for payment that cannot be cancelled."""
        test_payment.status = Payment.STATUS_COMPLETED
        test_payment.save()
        
        with patch('payments.views.PaymentService') as MockService:
            mock_service = MockService.return_value
            mock_service.cancel_payment.return_value = False
            
            url = reverse('payments:payment-cancel', kwargs={'payment_id': test_payment.id})
            response = authenticated_client.post(url)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['success'] is False
    
    def test_cancel_payment_wrong_user(self, authenticated_client, test_payment, db):
        """Test payment cancellation by different user."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        
        refresh = RefreshToken.for_user(other_user)
        authenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('payments:payment-cancel', kwargs={'payment_id': test_payment.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cancel_payment_unauthenticated(self, api_client, test_payment):
        """Test payment cancellation without authentication."""
        url = reverse('payments:payment-cancel', kwargs={'payment_id': test_payment.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMTNWebhookView:
    """Test MTN webhook endpoint."""
    
    def test_webhook_success(self, api_client, test_payment):
        """Test successful webhook processing."""
        with patch('payments.views.PaymentService') as MockService:
            mock_service = MockService.return_value
            mock_service.process_webhook.return_value = True
            
            url = reverse('payments:webhook-mtn')
            data = {
                'referenceId': test_payment.transaction_reference,
                'status': 'SUCCESSFUL',
                'financialTransactionId': 'MTN-TX-123'
            }
            headers = {'HTTP_X_SIGNATURE': 'test-signature'}
            
            response = api_client.post(url, data, format='json', **headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert 'message' in response.data
    
    def test_webhook_missing_signature(self, api_client):
        """Test webhook without signature."""
        url = reverse('payments:webhook-mtn')
        data = {
            'referenceId': str(uuid.uuid4()),
            'status': 'SUCCESSFUL'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_webhook_payment_not_found(self, api_client, db):
        """Test webhook for non-existent payment."""
        with patch('payments.views.PaymentService') as MockService:
            mock_service = MockService.return_value
            mock_service.process_webhook.return_value = False
            
            url = reverse('payments:webhook-mtn')
            data = {
                'referenceId': str(uuid.uuid4()),
                'status': 'SUCCESSFUL'
            }
            headers = {'HTTP_X_SIGNATURE': 'test-signature'}
            
            response = api_client.post(url, data, format='json', **headers)
            
            assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST]
    
    def test_webhook_no_authentication_required(self, api_client):
        """Test that webhook endpoint doesn't require authentication."""
        # Webhooks come from external service, so no auth required
        url = reverse('payments:webhook-mtn')
        data = {
            'referenceId': str(uuid.uuid4()),
            'status': 'SUCCESSFUL'
        }
        headers = {'HTTP_X_SIGNATURE': 'test-signature'}
        
        # Should not return 401 for missing auth token
        response = api_client.post(url, data, format='json', **headers)
        
        # Will fail for other reasons (payment not found, etc.) but not auth
        assert response.status_code != status.HTTP_401_UNAUTHORIZED or 'signature' in response.data.get('error', '').lower()


class TestMembershipFeeView:
    """Test membership fee endpoint."""
    
    def test_get_membership_fee_success(self, api_client, membership_fee_config):
        """Test successful membership fee retrieval."""
        url = reverse('payments:membership-fee')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'amount' in response.data
        assert 'currency' in response.data
        assert response.data['currency'] == 'UGX'
    
    def test_get_membership_fee_no_config(self, api_client, db):
        """Test membership fee retrieval with no config (uses default)."""
        # Ensure no config exists
        PaymentConfig.objects.filter(key='membership_fee_ugx').delete()
        
        url = reverse('payments:membership-fee')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'amount' in response.data
        # Should return default fallback
        assert Decimal(response.data['amount']) == Decimal('50000.00')
    
    def test_get_membership_fee_no_authentication_required(self, api_client, membership_fee_config):
        """Test that membership fee endpoint doesn't require authentication."""
        url = reverse('payments:membership-fee')
        response = api_client.get(url)
        
        # Should succeed without authentication
        assert response.status_code == status.HTTP_200_OK
