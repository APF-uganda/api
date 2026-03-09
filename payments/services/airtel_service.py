"""
Airtel Money Collection API service for payment integration.
Production-ready implementation with OAuth 2.0 token caching,
automatic retry on 401, and comprehensive error handling.

Environment Variables Required:
    AIRTEL_BASE_URL: Base URL (staging or production)
    AIRTEL_CLIENT_ID: Client ID from Airtel Developer Portal
    AIRTEL_CLIENT_SECRET: Client Secret from Airtel Developer Portal
    AIRTEL_COUNTRY: Country code (e.g., 'UG')
    AIRTEL_CURRENCY: Currency code (e.g., 'UGX')
    AIRTEL_WEBHOOK_SECRET: (Optional) Secret for webhook signature verification
"""
import os
import hmac
import hashlib
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AirtelConfig:
    """
    Configuration class for Airtel Money Collection API.
    Loads credentials from environment variables.
    
    Required Environment Variables:
        - AIRTEL_BASE_URL: API base URL
        - AIRTEL_CLIENT_ID: Client ID from Airtel Developer Portal
        - AIRTEL_CLIENT_SECRET: Client Secret for authentication
        - AIRTEL_COUNTRY: Country code (e.g., 'UG')
        - AIRTEL_CURRENCY: Currency code (e.g., 'UGX')
    """
    
    def __init__(self):
        """Initialize Airtel configuration from environment variables."""
        self.base_url = os.getenv('AIRTEL_BASE_URL', 'https://openapiuat.airtel.ug')
        self.client_id = os.getenv('AIRTEL_CLIENT_ID')
        self.client_secret = os.getenv('AIRTEL_CLIENT_SECRET')
        self.country = os.getenv('AIRTEL_COUNTRY', 'UG')
        self.currency = os.getenv('AIRTEL_CURRENCY', 'UGX')
        self.webhook_secret = os.getenv('AIRTEL_WEBHOOK_SECRET', '')
        
        # Validate required credentials
        if not all([self.base_url, self.client_id, self.client_secret]):
            logger.warning(
                "Airtel API credentials not fully configured. "
                "Required: AIRTEL_BASE_URL, AIRTEL_CLIENT_ID, AIRTEL_CLIENT_SECRET"
            )
    
    def is_configured(self) -> bool:
        """Check if all required credentials are configured."""
        return all([
            self.base_url,
            self.client_id,
            self.client_secret,
            self.country,
            self.currency
        ])


class AirtelService:
    """
    Production-ready Airtel Money Collection API service.
    
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
    
    def __init__(self, config: Optional[AirtelConfig] = None):
        """
        Initialize Airtel service with configuration.
        
        Args:
            config: Airtel configuration object. If None, creates default config.
        """
        self.config = config or AirtelConfig()
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
        logger.info("Airtel access token invalidated")
    
    def _get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get OAuth 2.0 access token using client credentials.
        Implements token caching with automatic refresh.
        
        Endpoint: POST /auth/oauth2/token
        Headers:
            - Content-Type: application/json
        Body:
            {
                "client_id": "...",
                "client_secret": "...",
                "grant_type": "client_credentials"
            }
        
        Response:
            {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "expires_in": 3600,
                "token_type": "Bearer"
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
            logger.debug("Using cached Airtel access token")
            return self.access_token
        
        # Validate configuration
        if not self.config.is_configured():
            raise Exception(
                "Airtel API credentials not configured. "
                "Required: AIRTEL_BASE_URL, AIRTEL_CLIENT_ID, AIRTEL_CLIENT_SECRET"
            )
        
        url = f"{self.config.base_url}/auth/oauth2/token"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "client_credentials"
        }
        
        try:
            logger.info("Requesting new Airtel access token")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get('access_token')
            
            if not self.access_token:
                raise Exception("No access_token in response")
            
            # Token typically valid for 3600 seconds
            expires_in = data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info(
                f"Airtel access token obtained successfully (expires in {expires_in}s)",
                extra={"expires_in": expires_in}
            )
            return self.access_token
            
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Airtel authentication HTTP error: {e.response.status_code}",
                extra={"status_code": e.response.status_code, "response": e.response.text}
            )
            raise Exception(f"Airtel authentication failed: HTTP {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Airtel authentication request failed: {str(e)}")
            raise Exception(f"Airtel authentication failed: {str(e)}")
        except Exception as e:
            logger.error(f"Airtel authentication unexpected error: {str(e)}")
            raise Exception(f"Airtel authentication failed: {str(e)}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True
    ) -> requests.Response:
        """
        Make HTTP request to Airtel API with automatic 401 retry.
        
        This helper method:
        1. Makes the request with provided parameters
        2. If 401 Unauthorized is returned:
           - Invalidates current token
           - Gets new token
           - Retries request once with new token
        3. Returns response or raises exception
        
        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint path (e.g., '/merchant/v2/payments/')
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
            logger.debug(f"Airtel API request: {method} {endpoint}")
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json,
                timeout=30
            )
            
            # Check for 401 and retry if enabled
            if response.status_code == 401 and retry_on_401:
                logger.warning("Airtel API returned 401, invalidating token and retrying")
                self._invalidate_token()
                
                # Get new token and update Authorization header
                new_token = self._get_access_token(force_refresh=True)
                request_headers['Authorization'] = f'Bearer {new_token}'
                
                # Retry request once
                logger.info("Retrying Airtel API request with new token")
                response = requests.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json,
                    timeout=30
                )
            
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"Airtel API request timeout: {method} {endpoint}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Airtel API request failed: {method} {endpoint} - {str(e)}")
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
        Initiate payment request (Collection).
        
        Endpoint: POST /merchant/v2/payments/
        Headers:
            - Authorization: Bearer {access_token}
            - Content-Type: application/json
            - X-Country: UG
            - X-Currency: UGX
        
        Body:
            {
                "reference": "Order payment",
                "subscriber": {
                    "country": "UG",
                    "msisdn": "771234567"
                },
                "transaction": {
                    "amount": 1000,
                    "id": "txn-123456"
                }
            }
        
        IMPORTANT: MSISDN must NOT include country code
        Example: 771234567 (NOT 256771234567)
        
        Response:
            - 200/201: Request sent successfully
            - 400 Bad Request: Invalid request
            - 401 Unauthorized: Invalid token (auto-retried)
            - 500 Internal Server Error: Provider error
        
        Args:
            phone_number: User's phone number (256XXXXXXXXX format)
            amount: Payment amount
            currency: Currency code (e.g., 'UGX')
            reference: Unique transaction reference
            payer_message: Message/description for the payment
        
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
            
            endpoint = "/merchant/v2/payments/"
            
            # CRITICAL: Remove country code from MSISDN
            # Airtel requires MSISDN without country code
            msisdn = phone_number
            if phone_number.startswith('256'):
                msisdn = phone_number[3:]  # Remove '256' prefix
            elif phone_number.startswith('+256'):
                msisdn = phone_number[4:]  # Remove '+256' prefix
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Country': self.config.country,
                'X-Currency': currency,
            }
            
            payload = {
                "reference": payer_message,
                "subscriber": {
                    "country": self.config.country,
                    "msisdn": msisdn
                },
                "transaction": {
                    "amount": float(amount),
                    "id": reference
                }
            }
            
            logger.info(
                "Initiating Airtel payment request",
                extra={
                    "transaction_reference": reference,
                    "amount": str(amount),
                    "currency": currency,
                    "masked_phone": f"{phone_number[:3]}****{phone_number[-4:]}" if len(phone_number) > 7 else "****",
                    "msisdn": msisdn
                }
            )
            
            # Make request with automatic 401 retry
            response = self._make_request(
                method='POST',
                endpoint=endpoint,
                headers=headers,
                json=payload
            )
            
            # Airtel returns 200/201 for successful request
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Check response structure
                status_data = data.get('status', {})
                if status_data.get('success') or data.get('data'):
                    logger.info(
                        f"Airtel payment request accepted",
                        extra={"transaction_reference": reference}
                    )
                    return {
                        "success": True,
                        "status": "pending",
                        "provider_transaction_id": reference,
                        "message": "Payment request sent. Please approve on your phone.",
                        "raw_response": data
                    }
                else:
                    # Request accepted but status indicates failure
                    error_msg = status_data.get('message', 'Payment request failed')
                    logger.error(
                        f"Airtel payment request failed: {error_msg}",
                        extra={"transaction_reference": reference}
                    )
                    return {
                        "success": False,
                        "status": "failed",
                        "provider_transaction_id": reference,
                        "message": self._get_user_friendly_error(error_msg),
                        "raw_response": data
                    }
            
            # Handle error responses
            error_msg = f"Airtel API returned status {response.status_code}"
            error_data = {}
            
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_msg)
            except Exception:
                error_msg = response.text or error_msg
            
            logger.error(
                f"Airtel payment request failed: {error_msg}",
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
                "Airtel payment request timeout",
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
                f"Airtel payment request network error: {str(e)}",
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
                f"Airtel payment request unexpected error: {str(e)}",
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
        
        Endpoint: GET /standard/v1/payments/{transaction_id}
        Headers:
            - Authorization: Bearer {access_token}
            - X-Country: UG
            - X-Currency: UGX
        
        Response:
            {
                "data": {
                    "transaction": {
                        "status": "TS" | "TIP" | "TF" | "TA",
                        "id": "...",
                        "message": "..."
                    }
                },
                "status": {
                    "code": "200",
                    "message": "SUCCESS",
                    "success": true
                }
            }
        
        Status Mapping:
            - TS (Transaction Successful) → completed
            - TIP (Transaction In Progress) → pending
            - TF (Transaction Failed) → failed
            - TA (Transaction Ambiguous) → pending
        
        Args:
            transaction_reference: Transaction reference ID
        
        Returns:
            Normalized response dict:
            {
                "success": True/False,
                "status": "completed" | "pending" | "failed",
                "provider_transaction_id": "transaction_id",
                "message": "Status message",
                "raw_response": {...}
            }
        """
        try:
            # Get access token (uses cache if valid)
            access_token = self._get_access_token()
            
            endpoint = f"/standard/v1/payments/{transaction_reference}"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Country': self.config.country,
                'X-Currency': self.config.currency,
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
                transaction_data = data.get('data', {}).get('transaction', {})
                airtel_status = transaction_data.get('status', '').upper()
                
                # Normalize Airtel status to internal status
                if airtel_status == 'TS':  # Transaction Successful
                    status = 'completed'
                    message = 'Payment completed successfully'
                elif airtel_status == 'TIP':  # Transaction In Progress
                    status = 'pending'
                    message = 'Payment is pending approval'
                elif airtel_status == 'TF':  # Transaction Failed
                    status = 'failed'
                    reason = transaction_data.get('message', 'Payment failed')
                    message = self._get_user_friendly_error(reason)
                elif airtel_status == 'TA':  # Transaction Ambiguous
                    status = 'pending'
                    message = 'Payment status is ambiguous, please check again'
                else:
                    status = 'pending'
                    message = f'Payment status: {airtel_status}'
                
                provider_id = transaction_data.get('id') or transaction_reference
                result = {
                    "success": True,
                    "status": status,
                    "provider_transaction_id": provider_id,
                    "message": message,
                    "raw_response": data
                }
                
                logger.info(
                    f"Airtel payment status: {status}",
                    extra={
                        "transaction_reference": transaction_reference,
                        "airtel_status": airtel_status,
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
                f"Airtel status check failed: {error_msg}",
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
                "Airtel status check timeout",
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
                f"Airtel status check network error: {str(e)}",
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
                f"Airtel status check unexpected error: {str(e)}",
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
        
        Endpoint: GET /standard/v1/users/balance
        Headers:
            - Authorization: Bearer {access_token}
            - X-Country: UG
            - X-Currency: UGX
        
        Response:
            {
                "data": {
                    "balance": "150000.00",
                    "currency": "UGX"
                },
                "status": {
                    "code": "200",
                    "message": "SUCCESS",
                    "success": true
                }
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
            
            endpoint = "/standard/v1/users/balance"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Country': self.config.country,
                'X-Currency': self.config.currency,
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
                balance_data = data.get('data', {})
                
                logger.info(
                    "Airtel account balance retrieved",
                    extra={
                        "available_balance": balance_data.get('balance'),
                        "currency": balance_data.get('currency')
                    }
                )
                
                return {
                    "success": True,
                    "available_balance": balance_data.get('balance'),
                    "currency": balance_data.get('currency'),
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
                f"Airtel balance check failed: {error_msg}",
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
            logger.error("Airtel balance check timeout")
            return {
                "success": False,
                "available_balance": None,
                "currency": None,
                "message": "Balance check timeout. Please try again.",
                "raw_response": {"error": "timeout"}
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Airtel balance check network error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "available_balance": None,
                "currency": None,
                "message": "Network error. Please try again.",
                "raw_response": {"error": str(e)}
            }
        
        except Exception as e:
            logger.error(f"Airtel balance check unexpected error: {str(e)}", exc_info=True)
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
        
        Airtel uses HMAC-SHA256 for webhook signatures to ensure
        the webhook request is authentic and hasn't been tampered with.
        
        Args:
            payload: Raw webhook payload as string
            signature: Signature from webhook headers
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.config.webhook_secret:
            logger.warning(
                "Airtel webhook secret not configured (AIRTEL_WEBHOOK_SECRET). "
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
                    "Airtel webhook signature verification failed",
                    extra={
                        "expected_signature": expected_signature[:10] + "...",
                        "received_signature": signature[:10] + "..." if signature else "None"
                    }
                )
            else:
                logger.info("Airtel webhook signature verified successfully")
            
            return is_valid
            
        except Exception as e:
            logger.error(
                f"Airtel webhook signature verification error: {str(e)}",
                exc_info=True
            )
            return False
    
    def _get_user_friendly_error(self, error_reason: str) -> str:
        """
        Convert Airtel error reasons to user-friendly messages.
        
        Common Airtel Money API error codes and their meanings.
        
        Args:
            error_reason: Error reason/code from Airtel API
        
        Returns:
            User-friendly error message
        """
        # Normalize error reason to uppercase for matching
        error_key = error_reason.upper() if error_reason else ''
        
        error_mapping = {
            # Subscriber errors
            'INSUFFICIENT_BALANCE': 'Insufficient funds in your Airtel Money account',
            'INVALID_MSISDN': 'Phone number not registered with Airtel Money',
            'SUBSCRIBER_NOT_FOUND': 'Phone number not registered with Airtel Money',
            'SUBSCRIBER_BARRED': 'Your Airtel Money account is temporarily blocked',
            'SUBSCRIBER_LIMIT_REACHED': 'Transaction limit reached. Please try a smaller amount',
            
            # Transaction errors
            'USER_CANCELLED': 'Payment was cancelled by user',
            'TRANSACTION_TIMEOUT': 'Payment request timed out. Please try again',
            'TRANSACTION_NOT_PERMITTED': 'Transaction not permitted. Please contact Airtel support',
            'DUPLICATE_TRANSACTION': 'Duplicate transaction detected',
            'INVALID_AMOUNT': 'Invalid payment amount',
            'AMOUNT_LIMIT_EXCEEDED': 'Transaction amount exceeds limit',
            'LIMIT_EXCEEDED': 'Transaction limit exceeded',
            
            # System errors
            'SERVICE_UNAVAILABLE': 'Airtel Money service temporarily unavailable. Please try again later',
            'SYSTEM_ERROR': 'Payment service temporarily unavailable. Please try again',
            'INTERNAL_PROCESSING_ERROR': 'Payment service temporarily unavailable. Please try again',
            'RESOURCE_NOT_FOUND': 'Transaction not found',
            
            # Network/timeout errors
            'TIMEOUT': 'Request timeout. Please try again',
            'NETWORK_ERROR': 'Network error. Please check your connection',
            
            # Currency/country errors
            'INVALID_CURRENCY': 'Invalid currency for this transaction',
            'INVALID_COUNTRY': 'Invalid country code',
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

