"""
Enhanced webhook views with security and tracking.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from payments.services.hybrid_payment_service import HybridPaymentService

logger = logging.getLogger(__name__)


class EnhancedMTNWebhookView(APIView):
    """
    POST /api/v1/payments/webhooks/mtn/
    Enhanced MTN Mobile Money webhook handler with security and tracking.
    """
    permission_classes = [AllowAny]  # Webhooks come from external service
    
    @swagger_auto_schema(
        operation_description="""
        Handle MTN Mobile Money webhook callback.
        
        Security:
        - Verifies HMAC-SHA256 signature
        - Validates payload structure
        - Idempotent processing (safe to retry)
        
        Tracking:
        - Records all webhook notifications
        - Maintains audit trail
        - Enables webhook-first with polling fallback
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['referenceId', 'status'],
            properties={
                'referenceId': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Transaction reference ID (UUID)'
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Payment status',
                    enum=['SUCCESSFUL', 'PENDING', 'FAILED']
                ),
                'financialTransactionId': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='MTN financial transaction ID'
                ),
                'amount': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Payment amount'
                ),
                'currency': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Currency code'
                ),
                'reason': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Failure reason (if status is FAILED)'
                ),
            }
        ),
        manual_parameters=[
            openapi.Parameter(
                'X-Signature',
                openapi.IN_HEADER,
                description='HMAC-SHA256 signature for webhook verification',
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Webhook processed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Bad Request - Invalid payload",
            401: "Unauthorized - Invalid signature",
            404: "Not Found - Payment not found",
            500: "Internal Server Error"
        },
        tags=['Payments - Webhooks']
    )
    def post(self, request):
        """
        Process MTN webhook callback with enhanced security.
        
        Steps:
        1. Extract and validate signature
        2. Process webhook using HybridPaymentService
        3. Return appropriate HTTP status
        """
        # Extract signature from headers
        signature = request.META.get('HTTP_X_SIGNATURE', '')
        
        if not signature:
            logger.warning(
                "MTN webhook received without signature",
                extra={"ip": self._get_client_ip(request)}
            )
            return Response({
                'error': 'Missing X-Signature header'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Log webhook receipt
        logger.info(
            "MTN webhook received",
            extra={
                "ip": self._get_client_ip(request),
                "reference_id": request.data.get('referenceId'),
                "webhook_status": request.data.get('status')
            }
        )
        
        # Process webhook
        payment_service = HybridPaymentService()
        success, message, http_status = payment_service.process_webhook_secure(
            provider='mtn',
            payload=request.data,
            signature=signature
        )
        
        # Return response
        if success:
            return Response({'message': message}, status=http_status)
        else:
            return Response({'error': message}, status=http_status)
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class EnhancedAirtelWebhookView(APIView):
    """
    POST /api/v1/payments/webhooks/airtel/
    Enhanced Airtel Money webhook handler with security and tracking.
    """
    permission_classes = [AllowAny]  # Webhooks come from external service
    
    @swagger_auto_schema(
        operation_description="""
        Handle Airtel Money webhook callback.
        
        Security:
        - Verifies HMAC-SHA256 signature
        - Validates payload structure
        - Idempotent processing (safe to retry)
        
        Tracking:
        - Records all webhook notifications
        - Maintains audit trail
        - Enables webhook-first with polling fallback
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['transaction'],
            properties={
                'transaction': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description='Transaction ID'
                        ),
                        'status': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description='Transaction status',
                            enum=['TS', 'TF', 'TA']
                        ),
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description='Status message'
                        ),
                    }
                )
            }
        ),
        manual_parameters=[
            openapi.Parameter(
                'X-Signature',
                openapi.IN_HEADER,
                description='HMAC-SHA256 signature for webhook verification',
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Webhook processed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Bad Request - Invalid payload",
            401: "Unauthorized - Invalid signature",
            404: "Not Found - Payment not found",
            500: "Internal Server Error"
        },
        tags=['Payments - Webhooks']
    )
    def post(self, request):
        """
        Process Airtel webhook callback with enhanced security.
        
        Steps:
        1. Extract and validate signature
        2. Process webhook using HybridPaymentService
        3. Return appropriate HTTP status
        """
        # Extract signature from headers
        signature = request.META.get('HTTP_X_SIGNATURE', '')
        
        if not signature:
            logger.warning(
                "Airtel webhook received without signature",
                extra={"ip": self._get_client_ip(request)}
            )
            return Response({
                'error': 'Missing X-Signature header'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Log webhook receipt
        transaction_data = request.data.get('transaction', {})
        logger.info(
            "Airtel webhook received",
            extra={
                "ip": self._get_client_ip(request),
                "transaction_id": transaction_data.get('id'),
                "webhook_status": transaction_data.get('status')
            }
        )
        
        # Process webhook
        payment_service = HybridPaymentService()
        success, message, http_status = payment_service.process_webhook_secure(
            provider='airtel',
            payload=request.data,
            signature=signature
        )
        
        # Return response
        if success:
            return Response({'message': message}, status=http_status)
        else:
            return Response({'error': message}, status=http_status)
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
