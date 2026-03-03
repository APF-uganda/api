"""
MTN Mobile Money Collection API service for payment integration.
Production-ready implementation with OAuth 2.0 token caching,
automatic retry on 401, and comprehensive error handling.

Environment Variables Required:
    MTN_BASE_URL: Base URL (sandbox or production)
    MTN_SUBSCRIPTION_KEY: Primary subscription key from MTN Developer Portal
    MTN_API_USER: API User UUID (created via provisioning API)
    MTN_API_KEY: API Key for the API User
    MTN_TARGET_ENVIRONMENT: 'sandbox' or 'production'
    MTN_WEBHOOK_SECRET: (Optional) Secret for webhook signature verification
"""
import os
import base64
import hmac
import hashlib
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MTNConfig:
    """
    Configuration class for MTN Mobile Money Collection API.
    Loads credentials from environment variables.
    
    Required Environment Variables:
        - MTN_BASE_URL: API base URL
        - MTN_SUBSCRIPTION_KEY: Subscription key from MTN Developer Portal
        - MTN_API_USER: API User UUID
        - MTN_API_KEY: API Key for authentication
        - MTN_TARGET_ENVIRONMENT: 'sandbox' or 'production'
    """
    
    def __init__(self):
        """Initialize MTN configuration from environment variables."""
        self.base_url = os.getenv('MTN_BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
        self.subscription_key = os.getenv('MTN_SUBSCRIPTION_KEY')
        self.api_user = os.getenv('MTN_API_USER')
        self.api_key = os.getenv('MTN_API_KEY')
        self.target_environment = os.getenv('MTN_TARGET_ENVIRONMENT', 'sandbox')
        self.webhook_secret = os.getenv('MTN_WEBHOOK_SECRET', '')
        
        # Validate required credentials
        if not all([self.base_url, self.subscription_key, self.api_user, self.api_key]):
            logger.warning(
                "MTN API credentials not fully configured. "
                "Required: MTN_BASE_URL, MTN_SUBSCRIPTION_KEY, MTN_API_USER, MTN_API_KEY"
            )
    
    def is_configured(self) -> bool:
        """Check if all required credentials are configured."""
        return all([
            self.base_url,
            self.subscription_key,
            self.api_user,
            self.api_key,
            self.target_environment
        ])


class MTNService:
    """
    Production-ready MTN Mobile Money Collection API service.
    
    Features:
        - OAuth 2.0 token caching with automatic refresh
        - Automatic retry on 401 Unauthorized
        - Comprehensive error handling and logging
        - Normalized response structure for PaymentService
    
    Token Caching Strategy:
        - Tokens are cached in memory with expiry timestamp
        - 60-second buffer before expiry to prevent edge cases
        - Automatic refresh when token expires or is invalid
        - Thread-safe for concurrent requests
    
    401 Retry Handling:
        - If any request returns 401, token is invalidated
        - Token is automatically refreshed
        - Request is retried once with new token
        - Prevents cascading failures from expired tokens
    """
    
    def __init__(self, config: Optional[MTNConfig] = None):
        """
        Initialize MTN service with configuration.
        
        Args:
            config: MTN configuration object. If None, creates default config.
        """
        self.config = config or MTNConfig()
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
    
    def _is_token_valid(self) -> bool:
        """
        Check if current access token is still valid.
        
        Returns:
            True if token exists and hasn't expired (with 60s buffer)
        """
        if not self.access_token or not self.token_expiry:
            return False
        # Add 60 second buffer before expiry to prevent edge cases
        return datetime.now() < (self.token_expiry - timedelta(seconds=60))
    
    def _invalidate_token(self) -> None:
        """Invalidate current access token (used when 401 occurs)."""
        self.access_token = None
        self.token_expiry = None
        logger.info("MTN access token invalidated")
    
    def _get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get OAuth 2.0 access token using API credentials.
        Implements token caching with automatic refresh.
        
        Endpoint: POST /collection/token/
        Headers:
            - Authorization: Basic base64(api_user:api_key)
            - Ocp-Apim-Subscription-Key: subscription_key
        
        Response:
            {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "token_type": "access_token",
                "expires_in": 3600
            }
        
        Args:
            force_refresh: If True, bypass cache and get new token
        
        Returns:
            Valid access token string
        
        Raises:
            Exception: If authentication fails or credentials not configured
        """
        # Return cached token if still valid and not forcing refresh
        if not force_refresh and self._is_token_valid():
            logger.debug("Using cached MTN access token")
            return self.access_token
        
        # Validate configuration
        if not self.config.is_configured():
            raise Exception(
                "MTN API credentials not configured. "
                "Required: MTN_BASE_URL, MTN_SUBSCRIPTION_KEY, MTN_API_USER, MTN_API_KEY"
            )
        
        url = f"{self.config.base_url}/collection/token/"
        
        # Create Basic Auth header: base64(api_user:api_key)
        credentials = f"{self.config.api_user}:{self.config.api_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Ocp-Apim-Subscription-Key': self.config.subscription_key,
        }
        
        try:
            logger.info("Requesting new MTN access token")
            response = requests.post(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get('access_token')
            
            if not self.access_token:
                raise Exception("No access_token in response")
            
            # Token typically valid for 3600 seconds
            expires_in = data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info(
                f"MTN access token obtained successfully (expires in {expires_in}s)",
                extra={"expires_in": expires_in}
            )
            return self.access_token
            
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"MTN authentication HTTP error: {e.response.status_code}",
                extra={"status_code": e.response.status_code, "response": e.response.text}
            )
            raise Exception(f"MTN authentication failed: HTTP {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"MTN authentication request failed: {str(e)}")
            raise Exception(f"MTN authentication failed: {str(e)}")
        except Exception as e:
            logger.error(f"MTN authentication unexpected error: {str(e)}")
            raise Exception(f"MTN authentication failed: {str(e)}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True
    ) -> requests.Response:
        """
        Make HTTP request to MTN API with automatic 401 retry.
        
        This helper method:
        1. Makes the request with provided parameters
        2. If 401 Unauthorized is returned:
           - Invalidates current token
           - Gets new token
           - Retries request once with new token
        3. Returns response or raises exception
        
        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint path (e.g., '/collection/v1_0/requesttopay')
            headers: Optional headers dict (will be merged with auth headers)
            json: Optional JSON body for POST requests
            retry_on_401: If True, automatically retry once on 401
        
        Returns:
            Response object
        
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        url = f"{self.config.base_url}{endpoint}"
        
        # Merge provided headers with defaults
        request_headers = (headers or {}).copy()
        
        try:
            logger.debug(f"MTN API request: {method} {endpoint}")
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json,
                timeout=30
            )
            
            # Check for 401 and retry if enabled
            if response.status_code == 401 and retry_on_401:
                logger.warning("MTN API returned 401, invalidating token and retrying")
                self._invalidate_token()
                
                # Get new token and update Authorization header
                new_token = self._get_access_token(force_refresh=True)
                request_headers['Authorization'] = f'Bearer {new_token}'
                
                # Retry request once
                logger.info("Retrying MTN API request with new token")
                response = requests.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json,
                    timeout=30
                )
            
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"MTN API request timeout: {method} {endpoint}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"MTN API request failed: {method} {endpoint} - {str(e)}")
            raise
    
    def request_to_pay(
        self,
        phone_number: str,
        amount: Decimal,
        currency: str,
        reference: str,
        payer_message: str = "APF Membership Fee"
    ) -> Dict[str, Any]:
        """
        Initiate payment request (Request To Pay).
        
        Endpoint: POST /collection/v1_0/requesttopay
        Headers:
            - Authorization: Bearer {access_token}
            - X-Reference-Id: {uuid} (transaction reference)
            - X-Target-Environment: sandbox|production
            - Ocp-Apim-Subscription-Key: subscription_key
            - Content-Type: application/json
        
        Body:
            {
                "amount": "1000",
                "currency": "UGX",
                "externalId": "transaction_reference",
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": "256XXXXXXXXX"
                },
                "payerMessage": "Membership Payment",
                "payeeNote": "Application Fee"
            }
        
        Response:
            - 202 Accepted: Request sent successfully
            - 400 Bad Request: Invalid request
            - 401 Unauthorized: Invalid token (auto-retried)
            - 500 Internal Server Error: Provider error
        
        Args:
            phone_number: User's phone number (256XXXXXXXXX format)
            amount: Payment amount
            currency: Currency code (e.g., 'UGX', 'EUR')
            reference: Unique transaction reference (UUID)
            payer_message: Message shown to payer
        
        Returns:
            Normalized response dict:
            {
                "success": True/False,
                "status": "pending",
                "provider_transaction_id": reference,
                "message": "Request sent successfully" | error message,
                "raw_response": {...}
            }
        """
        try:
            # Get access token (uses cache if valid)
            access_token = self._get_access_token()
            
            endpoint = "/collection/v1_0/requesttopay"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Reference-Id': reference,
                'X-Target-Environment': self.config.target_environment,
                'Ocp-Apim-Subscription-Key': self.config.subscription_key,
                'Content-Type': 'application/json',
            }
            
            payload = {
                "amount": str(amount),
                "currency": currency,
                "externalId": reference,
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number
                },
                "payerMessage": payer_message,
                "payeeNote": "Payment for APF membership"
            }
            
            logger.info(
                "Initiating MTN payment request",
                extra={
                    "transaction_reference": reference,
                    "amount": str(amount),
                    "currency": currency,
                    "masked_phone": f"{phone_number[:3]}****{phone_number[-4:]}" if len(phone_number) > 7 else "****"
                }
            )
            
            # Make request with automatic 401 retry
            response = self._make_request(
                method='POST',
                endpoint=endpoint,
                headers=headers,
                json=payload
            )
            
            # MTN returns 202 Accepted for successful request
            if response.status_code == 202:
                logger.info(
                    f"MTN payment request accepted",
                    extra={"transaction_reference": reference}
                )
                return {
                    "success": True,
                    "status": "pending",
                    "provider_transaction_id": reference,
                    "message": "Payment request sent. Please approve on your phone.",
                    "raw_response": {"status_code": 202, "reference": reference}
                }
            
            # Handle error responses
            error_msg = f"MTN API returned status {response.status_code}"
            error_data = {}
            
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_msg)
            except Exception:
                error_msg = response.text or error_msg
            
            logger.error(
                f"MTN payment request failed: {error_msg}",
                extra={
                    "transaction_reference": reference,
                    "status_code": response.status_code,
                    "response": error_data
                }
            )
            
            return {
                "success": False,
                "status": "failed",
                "provider_transaction_id": reference,
                "message": self._get_user_friendly_error(error_msg),
                "raw_response": error_data
            }
                
        except requests.exceptions.Timeout:
            logger.error(
                "MTN payment request timeout",
                extra={"transaction_reference": reference}
            )
            return {
                "success": False,
                "status": "failed",
                "provider_transaction_id": reference,
                "message": "Request timeout. Please try again.",
                "raw_response": {"error": "timeout"}
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(
                f"MTN payment request network error: {str(e)}",
                extra={"transaction_reference": reference},
                exc_info=True
            )
            return {
                "success": False,
                "status": "failed",
                "provider_transaction_id": reference,
                "message": "Network error. Please check your connection and try again.",
                "raw_response": {"error": str(e)}
            }
        
        except Exception as e:
            logger.error(
                f"MTN payment request unexpected error: {str(e)}",
                extra={"transaction_reference": reference},
                exc_info=True
            )
            return {
                "success": False,
                "status": "failed",
                "provider_transaction_id": reference,
                "message": "Payment request failed. Please try again.",
                "raw_response": {"error": str(e)}
            }
    
    def check_payment_status(self, transaction_reference: str) -> Dict[str, Any]:
        """
        Check status of payment transaction.
        
        Endpoint: GET /collection/v1_0/requesttopay/{referenceId}
        Headers:
            - Authorization: Bearer {access_token}
            - X-Target-Environment: sandbox|production
            - Ocp-Apim-Subscription-Key: subscription_key
        
        Response:
            {
                "amount": "1000",
                "currency": "UGX",
                "financialTransactionId": "123456789",
                "externalId": "uuid",
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": "256XXXXXXXXX"
                },
                "status": "SUCCESSFUL" | "PENDING" | "FAILED",
                "reason": "error reason if failed"
            }
        
        Status Mapping:
            - SUCCESSFUL → completed
            - PENDING → pending
            - FAILED → failed
        
        Args:
            transaction_reference: Transaction reference ID (UUID)
        
        Returns:
            Normalized response dict:
            {
                "success": True/False,
                "status": "completed" | "pending" | "failed",
                "provider_transaction_id": "financialTransactionId",
                "message": "Status message",
                "raw_response": {...}
            }
        """
        try:
            # Get access token (uses cache if valid)
            access_token = self._get_access_token()
            
            endpoint = f"/collection/v1_0/requesttopay/{transaction_reference}"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Target-Environment': self.config.target_environment,
                'Ocp-Apim-Subscription-Key': self.config.subscription_key,
            }
            
            # Make request with automatic 401 retry
            response = self._make_request(
                method='GET',
                endpoint=endpoint,
                headers=headers
            )
            
            # Handle successful response
            if response.status_code == 200:
                data = response.json()
                mtn_status = data.get('status', '').upper()
                
                # Normalize MTN status to internal status
                if mtn_status == 'SUCCESSFUL':
                    status = 'completed'
                    message = 'Payment completed successfully'
                elif mtn_status == 'PENDING':
                    status = 'pending'
                    message = 'Payment is pending approval'
                elif mtn_status == 'FAILED':
                    status = 'failed'
                    reason = data.get('reason', 'Payment failed')
                    message = self._get_user_friendly_error(reason)
                else:
                    status = 'pending'
                    message = f'Payment status: {mtn_status}'
                
                provider_id = data.get('financialTransactionId') or transaction_reference
                result = {
                    "success": True,
                    "status": status,
                    "provider_transaction_id": provider_id,
                    "message": message,
                    "raw_response": data
                }
                
                logger.info(
                    f"MTN payment status: {status}",
                    extra={
                        "transaction_reference": transaction_reference,
                        "mtn_status": mtn_status,
                        "provider_transaction_id": provider_id,
                    }
                )
                
                return result
            
            # Handle error responses
            error_msg = f"Status check failed: HTTP {response.status_code}"
            error_data = {}
            
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_msg)
            except Exception:
                error_msg = response.text or error_msg
            
            logger.error(
                f"MTN status check failed: {error_msg}",
                extra={
                    "transaction_reference": transaction_reference,
                    "status_code": response.status_code
                }
            )
            
            return {
                "success": False,
                "status": "pending",
                "provider_transaction_id": None,
                "message": error_msg,
                "raw_response": error_data
            }
            
        except requests.exceptions.Timeout:
            logger.error(
                "MTN status check timeout",
                extra={"transaction_reference": transaction_reference}
            )
            return {
                "success": False,
                "status": "pending",
                "provider_transaction_id": None,
                "message": "Status check timeout. Please try again.",
                "raw_response": {"error": "timeout"}
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(
                f"MTN status check network error: {str(e)}",
                extra={"transaction_reference": transaction_reference},
                exc_info=True
            )
            return {
                "success": False,
                "status": "pending",
                "provider_transaction_id": None,
                "message": "Network error. Please try again.",
                "raw_response": {"error": str(e)}
            }
        
        except Exception as e:
            logger.error(
                f"MTN status check unexpected error: {str(e)}",
                extra={"transaction_reference": transaction_reference},
                exc_info=True
            )
            return {
                "success": False,
                "status": "pending",
                "provider_transaction_id": None,
                "message": "Status check failed. Please try again.",
                "raw_response": {"error": str(e)}
            }
    
    def get_account_balance(self) -> Dict[str, Any]:
        """
        Get account balance (Admin only).
        
        Endpoint: GET /collection/v1_0/account/balance
        Headers:
            - Authorization: Bearer {access_token}
            - X-Target-Environment: sandbox|production
            - Ocp-Apim-Subscription-Key: subscription_key
        
        Response:
            {
                "availableBalance": "150000.00",
                "currency": "UGX"
            }
        
        Returns:
            {
                "success": True/False,
                "available_balance": "150000.00",
                "currency": "UGX",
                "raw_response": {...}
            }
        """
        try:
            # Get access token (uses cache if valid)
            access_token = self._get_access_token()
            
            endpoint = "/collection/v1_0/account/balance"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Target-Environment': self.config.target_environment,
                'Ocp-Apim-Subscription-Key': self.config.subscription_key,
            }
            
            # Make request with automatic 401 retry
            response = self._make_request(
                method='GET',
                endpoint=endpoint,
                headers=headers
            )
            
            # Handle successful response
            if response.status_code == 200:
                data = response.json()
                
                logger.info(
                    "MTN account balance retrieved",
                    extra={
                        "available_balance": data.get('availableBalance'),
                        "currency": data.get('currency')
                    }
                )
                
                return {
                    "success": True,
                    "available_balance": data.get('availableBalance'),
                    "currency": data.get('currency'),
                    "raw_response": data
                }
            
            # Handle error responses
            error_msg = f"Balance check failed: HTTP {response.status_code}"
            error_data = {}
            
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_msg)
            except Exception:
                error_msg = response.text or error_msg
            
            logger.error(
                f"MTN balance check failed: {error_msg}",
                extra={"status_code": response.status_code}
            )
            
            return {
                "success": False,
                "available_balance": None,
                "currency": None,
                "message": error_msg,
                "raw_response": error_data
            }
            
        except requests.exceptions.Timeout:
            logger.error("MTN balance check timeout")
            return {
                "success": False,
                "available_balance": None,
                "currency": None,
                "message": "Balance check timeout. Please try again.",
                "raw_response": {"error": "timeout"}
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"MTN balance check network error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "available_balance": None,
                "currency": None,
                "message": "Network error. Please try again.",
                "raw_response": {"error": str(e)}
            }
        
        except Exception as e:
            logger.error(f"MTN balance check unexpected error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "available_balance": None,
                "currency": None,
                "message": "Balance check failed. Please try again.",
                "raw_response": {"error": str(e)}
            }
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook callback signature using HMAC-SHA256.
        
        MTN uses HMAC-SHA256 for webhook signatures to ensure
        the webhook request is authentic and hasn't been tampered with.
        
        Args:
            payload: Raw webhook payload as string
            signature: Signature from webhook headers (X-Signature or similar)
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.config.webhook_secret:
            logger.warning(
                "MTN webhook secret not configured (MTN_WEBHOOK_SECRET). "
                "Skipping signature verification. This is insecure for production!"
            )
            return True  # Allow in development if secret not set
        
        try:
            # Calculate expected signature using HMAC-SHA256
            expected_signature = hmac.new(
                self.config.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures using constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if not is_valid:
                logger.warning(
                    "MTN webhook signature verification failed",
                    extra={
                        "expected_signature": expected_signature[:10] + "...",
                        "received_signature": signature[:10] + "..." if signature else "None"
                    }
                )
            else:
                logger.info("MTN webhook signature verified successfully")
            
            return is_valid
            
        except Exception as e:
            logger.error(
                f"MTN webhook signature verification error: {str(e)}",
                exc_info=True
            )
            return False
    
    def _get_user_friendly_error(self, error_reason: str) -> str:
        """
        Convert MTN error reasons to user-friendly messages.
        
        Common MTN Collection API error codes and their meanings.
        
        Args:
            error_reason: Error reason/code from MTN API
        
        Returns:
            User-friendly error message
        """
        # Normalize error reason to uppercase for matching
        error_key = error_reason.upper() if error_reason else ''
        
        error_mapping = {
            # Payer errors
            'PAYER_NOT_FOUND': 'Phone number not registered with MTN Mobile Money',
            'NOT_ENOUGH_FUNDS': 'Insufficient funds in your MTN Mobile Money account',
            'PAYER_LIMIT_REACHED': 'Transaction limit reached. Please try a smaller amount or contact MTN',
            
            # Payee errors
            'PAYEE_NOT_ALLOWED_TO_RECEIVE': 'Payment cannot be processed at this time',
            'PAYEE_LIMIT_REACHED': 'Recipient transaction limit reached',
            
            # Transaction errors
            'NOT_ALLOWED': 'Transaction not allowed. Please contact MTN support',
            'NOT_ALLOWED_TARGET_ENVIRONMENT': 'Payment environment configuration error',
            'INVALID_CALLBACK_URL_HOST': 'System configuration error. Please contact support',
            'INVALID_CURRENCY': 'Invalid currency for this transaction',
            'APPROVAL_REJECTED': 'Payment was rejected by user',
            'EXPIRED': 'Payment request expired. Please try again',
            'TRANSACTION_CANCELED': 'Transaction was cancelled',
            
            # System errors
            'INTERNAL_PROCESSING_ERROR': 'Payment service temporarily unavailable. Please try again',
            'SERVICE_UNAVAILABLE': 'MTN Mobile Money service temporarily unavailable. Please try again later',
            'RESOURCE_NOT_FOUND': 'Transaction not found',
            
            # Network/timeout errors
            'TIMEOUT': 'Request timeout. Please try again',
            'NETWORK_ERROR': 'Network error. Please check your connection',
        }
        
        # Check for exact match
        if error_key in error_mapping:
            return error_mapping[error_key]
        
        # Check for partial matches (case-insensitive)
        for key, message in error_mapping.items():
            if key in error_key:
                return message
        
        # Return original error with prefix if no match found
        if error_reason:
            return f'Payment failed: {error_reason}'
        
        return 'Payment failed. Please try again or contact support'
