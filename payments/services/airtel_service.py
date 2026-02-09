"""
Airtel Money service for payment integration.
Handles all Airtel Money API interactions including authentication,
payment requests, and status checking.
"""
import os
import uuid
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
    Configuration class for Airtel Money API.
    Loads credentials from environment variables and determines
    sandbox vs production base URL.
    """
    
    BASE_URL_SANDBOX = 'https://openapiuat.airtel.africa'
    BASE_URL_PRODUCTION = 'https://openapi.airtel.africa'
    
    def __init__(self):
        """Initialize Airtel configuration from environment variables."""
        self.client_id = os.getenv('AIRTEL_CLIENT_ID')
        self.client_secret = os.getenv('AIRTEL_CLIENT_SECRET')
        self.environment = os.getenv('PAYMENT_ENVIRONMENT', 'sandbox')
        self.webhook_secret = os.getenv('AIRTEL_WEBHOOK_SECRET', '')
        
        # Validate required credentials
        if not all([self.client_id, self.client_secret]):
            logger.warning(
                "Airtel API credentials not fully configured. "
                "Set AIRTEL_CLIENT_ID and AIRTEL_CLIENT_SECRET environment variables."
            )
    
    @property
    def base_url(self) -> str:
        """Return appropriate base URL based on environment."""
        if self.environment == 'production':
            return self.BASE_URL_PRODUCTION
        return self.BASE_URL_SANDBOX
    
    def is_configured(self) -> bool:
        """Check if all required credentials are configured."""
        return all([self.client_id, self.client_secret])



class AirtelService:
    """
    Service class for Airtel Money API integration.
    Handles OAuth 2.0 authentication, payment requests, and status checking.
    """
    
    def __init__(self, config: Optional[AirtelConfig] = None):
        """
        Initialize Airtel service.
        
        Args:
            config: Airtel configuration object. If None, creates default config.
        """
        self.config = config or AirtelConfig()
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
    
    def _get_base_url(self) -> str:
        """Return appropriate base URL based on environment."""
        return self.config.base_url
    
    def _is_token_valid(self) -> bool:
        """Check if current access token is still valid."""
        if not self.access_token or not self.token_expiry:
            return False
        # Add 60 second buffer before expiry
        return datetime.now() < (self.token_expiry - timedelta(seconds=60))
    
    def _get_access_token(self) -> str:
        """
        Get OAuth 2.0 access token.
        
        Endpoint: POST /auth/oauth2/token
        Headers:
            - Content-Type: application/json
        Body:
            {
                "client_id": "...",
                "client_secret": "...",
                "grant_type": "client_credentials"
            }
        
        Returns:
            access_token (valid for 7200 seconds)
        
        Raises:
            Exception: If authentication fails
        """
        # Return cached token if still valid
        if self._is_token_valid():
            return self.access_token
        
        if not self.config.is_configured():
            raise Exception("Airtel API credentials not configured")
        
        url = f"{self._get_base_url()}/auth/oauth2/token"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "client_credentials"
        }
        
        try:
            logger.info("Requesting Airtel access token")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get('access_token')
            
            # Token typically valid for 7200 seconds (2 hours)
            expires_in = data.get('expires_in', 7200)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("Airtel access token obtained successfully")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Airtel access token: {str(e)}")
            raise Exception(f"Airtel authentication failed: {str(e)}")

    
    def request_to_pay(
        self,
        phone_number: str,
        amount: Decimal,
        currency: str,
        reference: str,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Initiate payment request (USSD Push).
        
        Endpoint: POST /merchant/v1/payments/
        Headers:
            - Authorization: Bearer {access_token}
            - Content-Type: application/json
            - X-Country: UG
            - X-Currency: UGX
        
        Body:
            {
                "reference": "bill-payment",
                "subscriber": {
                    "country": "UG",
                    "currency": "UGX",
                    "msisdn": 708658321
                },
                "transaction": {
                    "amount": 5000,
                    "country": "UG",
                    "currency": "UGX",
                    "id": "unique-transaction-id"
                }
            }
        
        Args:
            phone_number: User's phone number (256XXXXXXXXX)
            amount: Payment amount
            currency: Currency code (e.g., 'UGX')
            reference: Unique transaction reference
            transaction_id: Unique transaction ID
        
        Returns:
            {
                "success": True/False,
                "transaction_reference": "...",
                "message": "..."
            }
        """
        try:
            # Get access token
            access_token = self._get_access_token()
            
            url = f"{self._get_base_url()}/merchant/v1/payments/"
            
            # Extract MSISDN (remove country code 256)
            msisdn = phone_number[3:] if phone_number.startswith('256') else phone_number
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Country': 'UG',
                'X-Currency': currency,
            }
            
            payload = {
                "reference": "bill-payment",
                "subscriber": {
                    "country": "UG",
                    "currency": currency,
                    "msisdn": msisdn
                },
                "transaction": {
                    "amount": float(amount),
                    "country": "UG",
                    "currency": currency,
                    "id": transaction_id
                }
            }
            
            logger.info(
                f"Initiating Airtel payment request",
                extra={
                    "transaction_reference": reference,
                    "transaction_id": transaction_id,
                    "amount": str(amount),
                    "currency": currency,
                    "masked_phone": f"{phone_number[:3]}****{phone_number[-4:]}"
                }
            )
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            # Airtel returns 200/201 for successful request
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Check if request was successful
                if data.get('status', {}).get('success'):
                    logger.info(f"Airtel payment request accepted: {reference}")
                    return {
                        "success": True,
                        "transaction_reference": reference,
                        "transaction_id": transaction_id,
                        "message": "Payment request sent. Please approve on your phone."
                    }
                else:
                    error_msg = data.get('status', {}).get('message', 'Payment request failed')
                    logger.error(
                        f"Airtel payment request failed: {error_msg}",
                        extra={"transaction_reference": reference}
                    )
                    return {
                        "success": False,
                        "transaction_reference": reference,
                        "message": error_msg
                    }
            else:
                error_msg = f"Airtel API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    pass
                
                logger.error(
                    f"Airtel payment request failed: {error_msg}",
                    extra={"transaction_reference": reference}
                )
                return {
                    "success": False,
                    "transaction_reference": reference,
                    "message": error_msg
                }
                
        except Exception as e:
            logger.error(
                f"Airtel payment request exception: {str(e)}",
                extra={"transaction_reference": reference},
                exc_info=True
            )
            return {
                "success": False,
                "transaction_reference": reference,
                "message": f"Payment request failed: {str(e)}"
            }

    
    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment transaction status.
        
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
                        "message": "...",
                        "id": "..."
                    }
                }
            }
        
        Status codes:
            - TS: Transaction Successful
            - TIP: Transaction In Progress
            - TF: Transaction Failed
            - TA: Transaction Ambiguous
        
        Args:
            transaction_id: Transaction ID
        
        Returns:
            {
                "success": True/False,
                "status": "completed" | "pending" | "failed",
                "provider_transaction_id": "...",
                "message": "..."
            }
        """
        try:
            # Get access token
            access_token = self._get_access_token()
            
            url = f"{self._get_base_url()}/standard/v1/payments/{transaction_id}"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Country': 'UG',
                'X-Currency': 'UGX',
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            transaction_data = data.get('data', {}).get('transaction', {})
            airtel_status = transaction_data.get('status', '').upper()
            
            # Normalize Airtel status to our internal status
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
                message = 'Payment status is ambiguous, checking...'
            else:
                status = 'pending'
                message = 'Payment status unknown'
            
            result = {
                "success": True,
                "status": status,
                "provider_transaction_id": transaction_data.get('id'),
                "message": message,
                "raw_response": data
            }
            
            logger.info(
                f"Airtel payment status checked: {status}",
                extra={"transaction_id": transaction_id}
            )
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Airtel status check failed: {str(e)}",
                extra={"transaction_id": transaction_id}
            )
            return {
                "success": False,
                "status": "pending",
                "provider_transaction_id": None,
                "message": f"Status check failed: {str(e)}"
            }

    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook callback signature.
        Airtel uses HMAC-SHA256 for webhook signatures.
        
        Args:
            payload: Raw webhook payload as string
            signature: Signature from webhook headers
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.config.webhook_secret:
            logger.warning("Airtel webhook secret not configured, skipping verification")
            return True  # Allow in development if secret not set
        
        try:
            # Calculate expected signature
            expected_signature = hmac.new(
                self.config.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (constant time comparison)
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if not is_valid:
                logger.warning("Airtel webhook signature verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Airtel webhook signature verification error: {str(e)}")
            return False
    
    def _get_user_friendly_error(self, error_reason: str) -> str:
        """
        Convert Airtel error reasons to user-friendly messages.
        
        Args:
            error_reason: Error reason from Airtel API
        
        Returns:
            User-friendly error message
        """
        error_mapping = {
            'INSUFFICIENT_BALANCE': 'Insufficient funds in your Airtel Money account',
            'INVALID_MSISDN': 'Phone number not registered with Airtel Money',
            'USER_CANCELLED': 'Payment cancelled by user',
            'TRANSACTION_TIMEOUT': 'Payment request timed out',
            'DUPLICATE_TRANSACTION': 'Duplicate transaction detected',
            'INVALID_AMOUNT': 'Invalid payment amount',
            'SERVICE_UNAVAILABLE': 'Airtel Money service temporarily unavailable',
            'SYSTEM_ERROR': 'Payment service temporarily unavailable',
            'TRANSACTION_NOT_PERMITTED': 'Transaction not permitted',
            'LIMIT_EXCEEDED': 'Transaction limit exceeded',
        }
        
        # Check if error reason contains any of the mapped keys
        for key, message in error_mapping.items():
            if key.lower() in error_reason.lower():
                return message
        
        return f'Payment failed: {error_reason}'
