"""
MTN Mobile Money service for payment integration.
Handles all MTN MoMo API interactions including authentication,
payment requests, and status checking.
"""
import os
import uuid
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
    Configuration class for MTN Mobile Money API.
    Loads credentials from environment variables and determines
    sandbox vs production base URL.
    """
    
    BASE_URL_SANDBOX = 'https://sandbox.momodeveloper.mtn.com'
    BASE_URL_PRODUCTION = 'https://momodeveloper.mtn.com'
    
    def __init__(self):
        """Initialize MTN configuration from environment variables."""
        self.api_user = os.getenv('MTN_API_USER')
        self.api_key = os.getenv('MTN_API_KEY')
        self.subscription_key = os.getenv('MTN_SUBSCRIPTION_KEY')
        self.environment = os.getenv('PAYMENT_ENVIRONMENT', 'sandbox')
        self.webhook_secret = os.getenv('MTN_WEBHOOK_SECRET', '')
        
        # Validate required credentials
        if not all([self.api_user, self.api_key, self.subscription_key]):
            logger.warning(
                "MTN API credentials not fully configured. "
                "Set MTN_API_USER, MTN_API_KEY, and MTN_SUBSCRIPTION_KEY environment variables."
            )
    
    @property
    def base_url(self) -> str:
        """Return appropriate base URL based on environment."""
        if self.environment == 'production':
            return self.BASE_URL_PRODUCTION
        return self.BASE_URL_SANDBOX
    
    @property
    def target_environment(self) -> str:
        """Return target environment for API headers."""
        return self.environment
    
    def is_configured(self) -> bool:
        """Check if all required credentials are configured."""
        return all([self.api_user, self.api_key, self.subscription_key])


class MTNService:
    """
    Service class for MTN Mobile Money API integration.
    Handles OAuth 2.0 authentication, payment requests, and status checking.
    """
    
    def __init__(self, config: Optional[MTNConfig] = None):
        """
        Initialize MTN service.
        
        Args:
            config: MTN configuration object. If None, creates default config.
        """
        self.config = config or MTNConfig()
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
        Get OAuth 2.0 access token using API credentials.
        Caches token until expiry.
        
        Endpoint: POST /collection/token/
        Headers:
            - Authorization: Basic base64(api_user:api_key)
            - Ocp-Apim-Subscription-Key: subscription_key
        
        Returns:
            access_token (valid for ~3600 seconds)
        
        Raises:
            Exception: If authentication fails
        """
        # Return cached token if still valid
        if self._is_token_valid():
            return self.access_token
        
        if not self.config.is_configured():
            raise Exception("MTN API credentials not configured")
        
        url = f"{self._get_base_url()}/collection/token/"
        
        # Create Basic Auth header
        credentials = f"{self.config.api_user}:{self.config.api_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Ocp-Apim-Subscription-Key': self.config.subscription_key,
        }
        
        try:
            logger.info("Requesting MTN access token")
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get('access_token')
            
            # Token typically valid for 3600 seconds
            expires_in = data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("MTN access token obtained successfully")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get MTN access token: {str(e)}")
            raise Exception(f"MTN authentication failed: {str(e)}")
    
    def request_to_pay(
        self,
        phone_number: str,
        amount: Decimal,
        currency: str,
        reference: str,
        payer_message: str = "APF Membership Fee"
    ) -> Dict[str, Any]:
        """
        Initiate payment request to user's phone.
        
        Endpoint: POST /collection/v1_0/requesttopay
        Headers:
            - Authorization: Bearer {access_token}
            - X-Reference-Id: {uuid}  # Transaction reference
            - X-Target-Environment: sandbox|production
            - Ocp-Apim-Subscription-Key: subscription_key
            - Content-Type: application/json
        
        Body:
            {
                "amount": "5000",
                "currency": "UGX",
                "externalId": "unique-reference",
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": "256XXXXXXXXX"
                },
                "payerMessage": "APF Membership Fee",
                "payeeNote": "Payment for membership"
            }
        
        Args:
            phone_number: User's phone number (256XXXXXXXXX)
            amount: Payment amount
            currency: Currency code (e.g., 'UGX')
            reference: Unique transaction reference
            payer_message: Message shown to payer
        
        Returns:
            {
                "success": True/False,
                "transaction_reference": "uuid",
                "message": "Request sent" | error message
            }
        """
        try:
            # Get access token
            access_token = self._get_access_token()
            
            url = f"{self._get_base_url()}/collection/v1_0/requesttopay"
            
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
                f"Initiating MTN payment request",
                extra={
                    "transaction_reference": reference,
                    "amount": str(amount),
                    "currency": currency,
                    "masked_phone": f"{phone_number[:3]}****{phone_number[-4:]}"
                }
            )
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            # MTN returns 202 Accepted for successful request
            if response.status_code == 202:
                logger.info(f"MTN payment request accepted: {reference}")
                return {
                    "success": True,
                    "transaction_reference": reference,
                    "message": "Payment request sent. Please approve on your phone."
                }
            else:
                error_msg = f"MTN API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    pass
                
                logger.error(
                    f"MTN payment request failed: {error_msg}",
                    extra={"transaction_reference": reference}
                )
                return {
                    "success": False,
                    "transaction_reference": reference,
                    "message": error_msg
                }
                
        except Exception as e:
            logger.error(
                f"MTN payment request exception: {str(e)}",
                extra={"transaction_reference": reference},
                exc_info=True
            )
            return {
                "success": False,
                "transaction_reference": reference,
                "message": f"Payment request failed: {str(e)}"
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
                "amount": "5000",
                "currency": "UGX",
                "financialTransactionId": "provider-tx-id",
                "externalId": "unique-reference",
                "payer": {...},
                "status": "SUCCESSFUL" | "PENDING" | "FAILED",
                "reason": "error reason if failed"
            }
        
        Args:
            transaction_reference: Transaction reference ID
        
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
            
            url = f"{self._get_base_url()}/collection/v1_0/requesttopay/{transaction_reference}"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Target-Environment': self.config.target_environment,
                'Ocp-Apim-Subscription-Key': self.config.subscription_key,
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            mtn_status = data.get('status', '').upper()
            
            # Normalize MTN status to our internal status
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
                message = 'Payment status unknown'
            
            result = {
                "success": True,
                "status": status,
                "provider_transaction_id": data.get('financialTransactionId'),
                "message": message,
                "raw_response": data
            }
            
            logger.info(
                f"MTN payment status checked: {status}",
                extra={"transaction_reference": transaction_reference}
            )
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(
                f"MTN status check failed: {str(e)}",
                extra={"transaction_reference": transaction_reference}
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
        MTN uses HMAC-SHA256 for webhook signatures.
        
        Args:
            payload: Raw webhook payload as string
            signature: Signature from webhook headers
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.config.webhook_secret:
            logger.warning("MTN webhook secret not configured, skipping verification")
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
                logger.warning("MTN webhook signature verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"MTN webhook signature verification error: {str(e)}")
            return False
    
    def _get_user_friendly_error(self, error_reason: str) -> str:
        """
        Convert MTN error reasons to user-friendly messages.
        
        Args:
            error_reason: Error reason from MTN API
        
        Returns:
            User-friendly error message
        """
        error_mapping = {
            'PAYER_NOT_FOUND': 'Phone number not registered with MTN Mobile Money',
            'NOT_ENOUGH_FUNDS': 'Insufficient funds in your MTN Mobile Money account',
            'PAYEE_NOT_ALLOWED_TO_RECEIVE': 'Payment cannot be processed',
            'PAYER_LIMIT_REACHED': 'Transaction limit reached',
            'PAYEE_LIMIT_REACHED': 'Recipient limit reached',
            'INTERNAL_PROCESSING_ERROR': 'Payment service temporarily unavailable',
            'NOT_ALLOWED': 'Payment not allowed',
            'NOT_ALLOWED_TARGET_ENVIRONMENT': 'Payment environment error',
            'INVALID_CALLBACK_URL_HOST': 'System configuration error',
            'INVALID_CURRENCY': 'Invalid currency',
            'SERVICE_UNAVAILABLE': 'MTN Mobile Money service temporarily unavailable',
        }
        
        return error_mapping.get(
            error_reason,
            f'Payment failed: {error_reason}'
        )
