"""
Payment Gateway - Unified interface for multiple payment providers.
Routes payment requests to MTN or Airtel based on provider parameter.

This gateway provides a consistent API for the rest of the application,
abstracting away provider-specific implementation details.

Usage:
    # Initialize gateway
    gateway = PaymentGateway()
    
    # Request payment
    result = gateway.request_payment(
        provider="mtn",  # or "airtel"
        phone_number="256771234567",
        amount=Decimal("5000"),
        currency="UGX",
        reference="txn-123456"
    )
    
    # Check payment status
    status = gateway.check_payment_status(
        provider="mtn",
        transaction_reference="txn-123456"
    )
    
    # Get account balance
    balance = gateway.get_account_balance(provider="mtn")
"""
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Literal
from .mtn_service import MTNService, MTNConfig
from .airtel_service import AirtelService, AirtelConfig

logger = logging.getLogger(__name__)

# Type alias for supported providers
Provider = Literal["mtn", "airtel"]


class PaymentGateway:
    """
    Unified payment gateway for multiple mobile money providers.
    
    This class provides a single interface for payment operations
    across different providers (MTN, Airtel, etc.).
    
    Features:
        - Provider-agnostic API
        - Automatic provider routing
        - Consistent response format
        - Centralized error handling
        - Easy to extend with new providers
    """
    
    # Supported providers
    SUPPORTED_PROVIDERS = ["mtn", "airtel"]
    
    def __init__(
        self,
        mtn_config: Optional[MTNConfig] = None,
        airtel_config: Optional[AirtelConfig] = None
    ):
        """
        Initialize payment gateway with provider configurations.
        
        Args:
            mtn_config: MTN configuration object (optional, uses defaults if None)
            airtel_config: Airtel configuration object (optional, uses defaults if None)
        """
        self.mtn_service = MTNService(config=mtn_config)
        self.airtel_service = AirtelService(config=airtel_config)
        
        logger.info("Payment gateway initialized")
    
    def _get_service(self, provider: str):
        """
        Get the appropriate service instance for the provider.
        
        Args:
            provider: Provider name ('mtn' or 'airtel')
        
        Returns:
            Service instance (MTNService or AirtelService)
        
        Raises:
            ValueError: If provider is not supported
        """
        provider_lower = provider.lower()
        
        if provider_lower == "mtn":
            return self.mtn_service
        elif provider_lower == "airtel":
            return self.airtel_service
        else:
            raise ValueError(
                f"Unsupported payment provider: {provider}. "
                f"Supported providers: {', '.join(self.SUPPORTED_PROVIDERS)}"
            )
    
    def is_provider_configured(self, provider: str) -> bool:
        """
        Check if a provider is properly configured.
        
        Args:
            provider: Provider name ('mtn' or 'airtel')
        
        Returns:
            True if provider is configured, False otherwise
        """
        try:
            service = self._get_service(provider)
            return service.config.is_configured()
        except ValueError:
            return False
    
    def get_configured_providers(self) -> list[str]:
        """
        Get list of configured providers.
        
        Returns:
            List of provider names that are properly configured
        """
        configured = []
        for provider in self.SUPPORTED_PROVIDERS:
            if self.is_provider_configured(provider):
                configured.append(provider)
        return configured
    
    def request_payment(
        self,
        provider: str,
        phone_number: str,
        amount: Decimal,
        currency: str,
        reference: str,
        payer_message: str = "APF Membership Fee"
    ) -> Dict[str, Any]:
        """
        Initiate payment request through specified provider.
        
        This method routes the payment request to the appropriate provider
        service and returns a normalized response.
        
        Args:
            provider: Payment provider ('mtn' or 'airtel')
            phone_number: User's phone number (256XXXXXXXXX format)
            amount: Payment amount
            currency: Currency code (e.g., 'UGX')
            reference: Unique transaction reference
            payer_message: Message shown to payer (optional)
        
        Returns:
            Normalized response dict:
            {
                "success": True/False,
                "status": "pending" | "completed" | "failed",
                "provider": "mtn" | "airtel",
                "provider_transaction_id": "...",
                "message": "...",
                "raw_response": {...}
            }
        
        Raises:
            ValueError: If provider is not supported
        """
        provider_lower = provider.lower()
        
        logger.info(
            f"Payment gateway: Routing payment request to {provider_lower}",
            extra={
                "provider": provider_lower,
                "transaction_reference": reference,
                "amount": str(amount),
                "currency": currency
            }
        )
        
        try:
            # Get appropriate service
            service = self._get_service(provider_lower)
            
            # Check if provider is configured
            if not service.config.is_configured():
                logger.error(
                    f"{provider_lower.upper()} provider not configured",
                    extra={"provider": provider_lower}
                )
                return {
                    "success": False,
                    "status": "failed",
                    "provider": provider_lower,
                    "provider_transaction_id": None,
                    "message": f"{provider_lower.upper()} payment service is not configured. Please contact support.",
                    "raw_response": {"error": "provider_not_configured"}
                }
            
            # Make payment request
            result = service.request_to_pay(
                phone_number=phone_number,
                amount=amount,
                currency=currency,
                reference=reference,
                payer_message=payer_message
            )
            
            # Add provider to response
            result["provider"] = provider_lower
            
            logger.info(
                f"Payment gateway: {provider_lower} request completed",
                extra={
                    "provider": provider_lower,
                    "transaction_reference": reference,
                    "success": result.get("success")
                }
            )
            
            return result
            
        except ValueError as e:
            # Invalid provider
            logger.error(f"Payment gateway: Invalid provider - {str(e)}")
            raise
        
        except Exception as e:
            # Unexpected error
            logger.error(
                f"Payment gateway: Unexpected error with {provider_lower}",
                extra={
                    "provider": provider_lower,
                    "transaction_reference": reference,
                    "error": str(e)
                },
                exc_info=True
            )
            return {
                "success": False,
                "status": "failed",
                "provider": provider_lower,
                "provider_transaction_id": None,
                "message": "Payment request failed due to system error. Please try again.",
                "raw_response": {"error": str(e)}
            }
    
    def check_payment_status(
        self,
        provider: str,
        transaction_reference: str
    ) -> Dict[str, Any]:
        """
        Check payment status through specified provider.
        
        Args:
            provider: Payment provider ('mtn' or 'airtel')
            transaction_reference: Transaction reference ID
        
        Returns:
            Normalized response dict:
            {
                "success": True/False,
                "status": "completed" | "pending" | "failed",
                "provider": "mtn" | "airtel",
                "provider_transaction_id": "...",
                "message": "...",
                "raw_response": {...}
            }
        
        Raises:
            ValueError: If provider is not supported
        """
        provider_lower = provider.lower()
        
        logger.info(
            f"Payment gateway: Checking payment status with {provider_lower}",
            extra={
                "provider": provider_lower,
                "transaction_reference": transaction_reference
            }
        )
        
        try:
            # Get appropriate service
            service = self._get_service(provider_lower)
            
            # Check if provider is configured
            if not service.config.is_configured():
                logger.error(
                    f"{provider_lower.upper()} provider not configured",
                    extra={"provider": provider_lower}
                )
                return {
                    "success": False,
                    "status": "pending",
                    "provider": provider_lower,
                    "provider_transaction_id": None,
                    "message": f"{provider_lower.upper()} payment service is not configured.",
                    "raw_response": {"error": "provider_not_configured"}
                }
            
            # Check payment status
            result = service.check_payment_status(transaction_reference)
            
            # Add provider to response
            result["provider"] = provider_lower
            
            logger.info(
                f"Payment gateway: {provider_lower} status check completed",
                extra={
                    "provider": provider_lower,
                    "transaction_reference": transaction_reference,
                    "status": result.get("status")
                }
            )
            
            return result
            
        except ValueError as e:
            # Invalid provider
            logger.error(f"Payment gateway: Invalid provider - {str(e)}")
            raise
        
        except Exception as e:
            # Unexpected error
            logger.error(
                f"Payment gateway: Unexpected error checking status with {provider_lower}",
                extra={
                    "provider": provider_lower,
                    "transaction_reference": transaction_reference,
                    "error": str(e)
                },
                exc_info=True
            )
            return {
                "success": False,
                "status": "pending",
                "provider": provider_lower,
                "provider_transaction_id": None,
                "message": "Status check failed. Please try again.",
                "raw_response": {"error": str(e)}
            }
    
    def get_account_balance(self, provider: str) -> Dict[str, Any]:
        """
        Get account balance for specified provider (Admin only).
        
        Args:
            provider: Payment provider ('mtn' or 'airtel')
        
        Returns:
            {
                "success": True/False,
                "provider": "mtn" | "airtel",
                "available_balance": "150000.00",
                "currency": "UGX",
                "message": "..." (only on error),
                "raw_response": {...}
            }
        
        Raises:
            ValueError: If provider is not supported
        """
        provider_lower = provider.lower()
        
        logger.info(
            f"Payment gateway: Getting account balance for {provider_lower}",
            extra={"provider": provider_lower}
        )
        
        try:
            # Get appropriate service
            service = self._get_service(provider_lower)
            
            # Check if provider is configured
            if not service.config.is_configured():
                logger.error(
                    f"{provider_lower.upper()} provider not configured",
                    extra={"provider": provider_lower}
                )
                return {
                    "success": False,
                    "provider": provider_lower,
                    "available_balance": None,
                    "currency": None,
                    "message": f"{provider_lower.upper()} payment service is not configured.",
                    "raw_response": {"error": "provider_not_configured"}
                }
            
            # Get account balance
            result = service.get_account_balance()
            
            # Add provider to response
            result["provider"] = provider_lower
            
            logger.info(
                f"Payment gateway: {provider_lower} balance retrieved",
                extra={
                    "provider": provider_lower,
                    "balance": result.get("available_balance"),
                    "currency": result.get("currency")
                }
            )
            
            return result
            
        except ValueError as e:
            # Invalid provider
            logger.error(f"Payment gateway: Invalid provider - {str(e)}")
            raise
        
        except Exception as e:
            # Unexpected error
            logger.error(
                f"Payment gateway: Unexpected error getting balance from {provider_lower}",
                extra={
                    "provider": provider_lower,
                    "error": str(e)
                },
                exc_info=True
            )
            return {
                "success": False,
                "provider": provider_lower,
                "available_balance": None,
                "currency": None,
                "message": "Balance check failed. Please try again.",
                "raw_response": {"error": str(e)}
            }
    
    def verify_webhook_signature(
        self,
        provider: str,
        payload: str,
        signature: str
    ) -> bool:
        """
        Verify webhook signature for specified provider.
        
        Args:
            provider: Payment provider ('mtn' or 'airtel')
            payload: Raw webhook payload as string
            signature: Signature from webhook headers
        
        Returns:
            True if signature is valid, False otherwise
        
        Raises:
            ValueError: If provider is not supported
        """
        provider_lower = provider.lower()
        
        try:
            service = self._get_service(provider_lower)
            return service.verify_webhook_signature(payload, signature)
        except ValueError as e:
            logger.error(f"Payment gateway: Invalid provider for webhook - {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Payment gateway: Error verifying webhook signature",
                extra={"provider": provider_lower, "error": str(e)},
                exc_info=True
            )
            return False


# Convenience function for quick access
def create_payment_gateway() -> PaymentGateway:
    """
    Create and return a PaymentGateway instance with default configurations.
    
    Returns:
        PaymentGateway instance
    """
    return PaymentGateway()
