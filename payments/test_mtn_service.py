"""
Unit tests for MTN Mobile Money service.
Tests authentication flow, payment requests, status checking, and error handling.
"""
import pytest
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from payments.services.mtn_service import MTNService, MTNConfig


class TestMTNConfig:
    """Test MTN configuration class."""
    
    def test_config_loads_from_environment(self):
        """Test that configuration loads from environment variables."""
        with patch.dict('os.environ', {
            'MTN_API_USER': 'test-user',
            'MTN_API_KEY': 'test-key',
            'MTN_SUBSCRIPTION_KEY': 'test-sub-key',
            'PAYMENT_ENVIRONMENT': 'sandbox'
        }):
            config = MTNConfig()
            assert config.api_user == 'test-user'
            assert config.api_key == 'test-key'
            assert config.subscription_key == 'test-sub-key'
            assert config.environment == 'sandbox'
    
    def test_base_url_sandbox(self):
        """Test that sandbox environment returns correct base URL."""
        with patch.dict('os.environ', {'PAYMENT_ENVIRONMENT': 'sandbox'}):
            config = MTNConfig()
            assert config.base_url == 'https://sandbox.momodeveloper.mtn.com'
    
    def test_base_url_production(self):
        """Test that production environment returns correct base URL."""
        with patch.dict('os.environ', {'PAYMENT_ENVIRONMENT': 'production'}):
            config = MTNConfig()
            assert config.base_url == 'https://momodeveloper.mtn.com'
    
    def test_is_configured_returns_true_when_all_credentials_present(self):
        """Test is_configured returns True when all credentials are set."""
        with patch.dict('os.environ', {
            'MTN_API_USER': 'test-user',
            'MTN_API_KEY': 'test-key',
            'MTN_SUBSCRIPTION_KEY': 'test-sub-key'
        }):
            config = MTNConfig()
            assert config.is_configured() is True
    
    def test_is_configured_returns_false_when_credentials_missing(self):
        """Test is_configured returns False when credentials are missing."""
        with patch.dict('os.environ', {}, clear=True):
            config = MTNConfig()
            assert config.is_configured() is False


class TestMTNService:
    """Test MTN service class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock MTN configuration."""
        config = Mock(spec=MTNConfig)
        config.api_user = 'test-user'
        config.api_key = 'test-key'
        config.subscription_key = 'test-sub-key'
        config.environment = 'sandbox'
        config.base_url = 'https://sandbox.momodeveloper.mtn.com'
        config.target_environment = 'sandbox'
        config.webhook_secret = 'test-secret'
        config.is_configured.return_value = True
        return config
    
    @pytest.fixture
    def mtn_service(self, mock_config):
        """Create MTN service instance with mock config."""
        return MTNService(config=mock_config)
    
    def test_service_initialization(self, mtn_service):
        """Test that service initializes correctly."""
        assert mtn_service.access_token is None
        assert mtn_service.token_expiry is None
    
    @patch('payments.services.mtn_service.requests.post')
    def test_get_access_token_success(self, mock_post, mtn_service):
        """Test successful access token retrieval."""
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test-token-123',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        token = mtn_service._get_access_token()
        
        assert token == 'test-token-123'
        assert mtn_service.access_token == 'test-token-123'
        assert mtn_service.token_expiry is not None
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'Authorization' in call_args[1]['headers']
        assert 'Ocp-Apim-Subscription-Key' in call_args[1]['headers']
    
    @patch('payments.services.mtn_service.requests.post')
    def test_get_access_token_caching(self, mock_post, mtn_service):
        """Test that access token is cached and reused."""
        # Mock successful token response
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test-token-123',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        # First call should request token
        token1 = mtn_service._get_access_token()
        assert mock_post.call_count == 1
        
        # Second call should use cached token
        token2 = mtn_service._get_access_token()
        assert mock_post.call_count == 1  # No additional call
        assert token1 == token2
    
    @patch('payments.services.mtn_service.requests.post')
    def test_get_access_token_refresh_on_expiry(self, mock_post, mtn_service):
        """Test that token is refreshed when expired."""
        # Mock successful token response
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test-token-123',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        # Get initial token
        mtn_service._get_access_token()
        assert mock_post.call_count == 1
        
        # Simulate token expiry
        mtn_service.token_expiry = datetime.now() - timedelta(seconds=10)
        
        # Next call should refresh token
        mtn_service._get_access_token()
        assert mock_post.call_count == 2
    
    @patch('payments.services.mtn_service.requests.post')
    def test_get_access_token_failure(self, mock_post, mtn_service):
        """Test handling of authentication failure."""
        # Mock failed response that raises an exception
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Auth failed")
        
        with pytest.raises(Exception) as exc_info:
            mtn_service._get_access_token()
        
        assert "MTN authentication failed" in str(exc_info.value)
    
    @patch('payments.services.mtn_service.requests.post')
    def test_request_to_pay_success(self, mock_post, mtn_service):
        """Test successful payment request."""
        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 3600
        }
        
        # Mock payment request (202 Accepted)
        payment_response = Mock()
        payment_response.status_code = 202
        
        mock_post.side_effect = [token_response, payment_response]
        
        reference = str(uuid.uuid4())
        result = mtn_service.request_to_pay(
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            currency='UGX',
            reference=reference
        )
        
        assert result['success'] is True
        assert result['transaction_reference'] == reference
        assert 'approve on your phone' in result['message'].lower()
    
    @patch('payments.services.mtn_service.requests.post')
    def test_request_to_pay_failure(self, mock_post, mtn_service):
        """Test failed payment request."""
        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 3600
        }
        
        # Mock payment request failure
        payment_response = Mock()
        payment_response.status_code = 400
        payment_response.json.return_value = {
            'message': 'Invalid phone number'
        }
        
        mock_post.side_effect = [token_response, payment_response]
        
        reference = str(uuid.uuid4())
        result = mtn_service.request_to_pay(
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            currency='UGX',
            reference=reference
        )
        
        assert result['success'] is False
        assert result['transaction_reference'] == reference
    
    @patch('payments.services.mtn_service.requests.post')
    @patch('payments.services.mtn_service.requests.get')
    def test_check_payment_status_successful(self, mock_get, mock_post, mtn_service):
        """Test checking status of successful payment."""
        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 3600
        }
        mock_post.return_value = token_response
        
        # Mock status check response
        status_response = Mock()
        status_response.json.return_value = {
            'status': 'SUCCESSFUL',
            'financialTransactionId': 'mtn-tx-123',
            'amount': '50000',
            'currency': 'UGX'
        }
        mock_get.return_value = status_response
        
        reference = str(uuid.uuid4())
        result = mtn_service.check_payment_status(reference)
        
        assert result['success'] is True
        assert result['status'] == 'completed'
        assert result['provider_transaction_id'] == 'mtn-tx-123'
    
    @patch('payments.services.mtn_service.requests.post')
    @patch('payments.services.mtn_service.requests.get')
    def test_check_payment_status_pending(self, mock_get, mock_post, mtn_service):
        """Test checking status of pending payment."""
        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 3600
        }
        mock_post.return_value = token_response
        
        # Mock status check response
        status_response = Mock()
        status_response.json.return_value = {
            'status': 'PENDING',
            'amount': '50000',
            'currency': 'UGX'
        }
        mock_get.return_value = status_response
        
        reference = str(uuid.uuid4())
        result = mtn_service.check_payment_status(reference)
        
        assert result['success'] is True
        assert result['status'] == 'pending'
    
    @patch('payments.services.mtn_service.requests.post')
    @patch('payments.services.mtn_service.requests.get')
    def test_check_payment_status_failed(self, mock_get, mock_post, mtn_service):
        """Test checking status of failed payment."""
        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 3600
        }
        mock_post.return_value = token_response
        
        # Mock status check response
        status_response = Mock()
        status_response.json.return_value = {
            'status': 'FAILED',
            'reason': 'NOT_ENOUGH_FUNDS',
            'amount': '50000',
            'currency': 'UGX'
        }
        mock_get.return_value = status_response
        
        reference = str(uuid.uuid4())
        result = mtn_service.check_payment_status(reference)
        
        assert result['success'] is True
        assert result['status'] == 'failed'
        assert 'insufficient funds' in result['message'].lower()
    
    @patch('payments.services.mtn_service.requests.post')
    @patch('payments.services.mtn_service.requests.get')
    def test_check_payment_status_network_error(self, mock_get, mock_post, mtn_service):
        """Test handling of network error during status check."""
        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            'access_token': 'test-token',
            'expires_in': 3600
        }
        mock_post.return_value = token_response
        
        # Mock network error with RequestException
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Network timeout")
        
        reference = str(uuid.uuid4())
        result = mtn_service.check_payment_status(reference)
        
        assert result['success'] is False
        assert result['status'] == 'pending'
    
    def test_verify_webhook_signature_valid(self, mtn_service):
        """Test webhook signature verification with valid signature."""
        payload = '{"status": "SUCCESSFUL"}'
        
        # Calculate correct signature
        import hmac
        import hashlib
        expected_signature = hmac.new(
            mtn_service.config.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        is_valid = mtn_service.verify_webhook_signature(payload, expected_signature)
        assert is_valid is True
    
    def test_verify_webhook_signature_invalid(self, mtn_service):
        """Test webhook signature verification with invalid signature."""
        payload = '{"status": "SUCCESSFUL"}'
        invalid_signature = 'invalid-signature-123'
        
        is_valid = mtn_service.verify_webhook_signature(payload, invalid_signature)
        assert is_valid is False
    
    def test_get_user_friendly_error_messages(self, mtn_service):
        """Test conversion of MTN error codes to user-friendly messages."""
        test_cases = [
            ('NOT_ENOUGH_FUNDS', 'insufficient funds'),
            ('PAYER_NOT_FOUND', 'not registered'),
            ('SERVICE_UNAVAILABLE', 'temporarily unavailable'),
        ]
        
        for error_code, expected_text in test_cases:
            message = mtn_service._get_user_friendly_error(error_code)
            assert expected_text.lower() in message.lower()
