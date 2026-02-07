"""
Payment API views for mobile money integration.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404

from .models import Payment
from .services.payment_service import PaymentService
from .serializers import (
    PaymentInitiationSerializer,
    PaymentInitiationResponseSerializer,
    PaymentStatusResponseSerializer,
    PaymentRetryResponseSerializer,
    PaymentCancellationResponseSerializer,
    MembershipFeeResponseSerializer
)

logger = logging.getLogger(__name__)


class PaymentInitiationView(APIView):
    """
    POST /api/v1/payments/initiate/
    Initiate a mobile money payment.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Initiate a mobile money payment for membership fee",
        request_body=PaymentInitiationSerializer,
        responses={
            200: openapi.Response(
                description="Payment initiated successfully",
                schema=PaymentInitiationResponseSerializer
            ),
            400: "Bad Request - Invalid input data",
            401: "Unauthorized - Authentication required",
            500: "Internal Server Error"
        },
        tags=['Payments']
    )
    def post(self, request):
        """
        Initiate payment request.
        
        Steps:
        1. Validate request data (phone, provider, amount)
        2. Get membership fee from configuration
        3. Call PaymentService.initiate_payment()
        4. Return payment ID and transaction reference
        
        Requirements: 1.3, 1.4
        """
        # Step 1: Validate request data
        serializer = PaymentInitiationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Invalid input data',
                    'details': serializer.errors
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        phone_number = validated_data['phone_number']
        provider = validated_data['provider']
        application_id = validated_data.get('application_id')
        
        # Step 2: Get membership fee from configuration
        payment_service = PaymentService()
        amount = payment_service.get_membership_fee()
        
        # Get client info for audit
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Step 3: Call PaymentService.initiate_payment()
        success, payment, message = payment_service.initiate_payment(
            user=request.user,
            phone_number=phone_number,
            amount=amount,
            provider=provider,
            application_id=application_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Step 4: Return payment ID and transaction reference
        if success:
            return Response({
                'success': True,
                'payment_id': str(payment.id),
                'transaction_reference': payment.transaction_reference,
                'message': message,
                'amount': str(payment.amount),
                'currency': payment.currency
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': {
                    'code': 'PAYMENT_INITIATION_FAILED',
                    'message': message
                }
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PaymentStatusView(APIView):
    """
    GET /api/v1/payments/status/{payment_id}/
    Check payment status.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Check the current status of a payment",
        manual_parameters=[
            openapi.Parameter(
                'payment_id',
                openapi.IN_PATH,
                description="Payment UUID",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID
            )
        ],
        responses={
            200: openapi.Response(
                description="Payment status retrieved successfully",
                schema=PaymentStatusResponseSerializer
            ),
            404: "Payment not found",
            401: "Unauthorized - Authentication required"
        },
        tags=['Payments']
    )
    def get(self, request, payment_id):
        """
        Check payment status.
        
        Steps:
        1. Get payment by ID
        2. Verify user owns the payment
        3. Call PaymentService.check_payment_status()
        4. Return current status and message
        
        Requirements: 1.6, 4.2
        """
        # Step 1: Get payment by ID
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Step 2: Verify user owns the payment
        if payment.user != request.user:
            return Response({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'You do not have permission to access this payment'
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Step 3: Call PaymentService.check_payment_status()
        payment_service = PaymentService()
        current_status, message = payment_service.check_payment_status(payment)
        
        # Step 4: Return current status and message
        return Response({
            'status': current_status,
            'message': message,
            'provider_transaction_id': payment.provider_transaction_id,
            'updated_at': payment.updated_at,
            'amount': str(payment.amount),
            'currency': payment.currency,
            'provider': payment.provider
        }, status=status.HTTP_200_OK)


class PaymentRetryView(APIView):
    """
    POST /api/v1/payments/{payment_id}/retry/
    Retry a failed payment.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Retry a failed or timed out payment",
        manual_parameters=[
            openapi.Parameter(
                'payment_id',
                openapi.IN_PATH,
                description="Payment UUID",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID
            )
        ],
        responses={
            200: openapi.Response(
                description="Payment retry initiated successfully",
                schema=PaymentRetryResponseSerializer
            ),
            400: "Bad Request - Payment cannot be retried",
            404: "Payment not found",
            401: "Unauthorized - Authentication required"
        },
        tags=['Payments']
    )
    def post(self, request, payment_id):
        """
        Retry failed payment.
        
        Steps:
        1. Get payment by ID
        2. Verify user owns the payment
        3. Call PaymentService.retry_payment()
        4. Return new payment ID
        
        Requirements: 12.1, 12.2
        """
        # Step 1: Get payment by ID
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Step 2: Verify user owns the payment
        if payment.user != request.user:
            return Response({
                'success': False,
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'You do not have permission to access this payment'
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Step 3: Call PaymentService.retry_payment()
        payment_service = PaymentService()
        success, new_payment, message = payment_service.retry_payment(payment)
        
        # Step 4: Return new payment ID
        if success:
            return Response({
                'success': True,
                'new_payment_id': str(new_payment.id),
                'transaction_reference': new_payment.transaction_reference,
                'message': message
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'new_payment_id': None,
                'transaction_reference': None,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)


class PaymentCancellationView(APIView):
    """
    POST /api/v1/payments/{payment_id}/cancel/
    Cancel a pending payment.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Cancel a pending payment",
        manual_parameters=[
            openapi.Parameter(
                'payment_id',
                openapi.IN_PATH,
                description="Payment UUID",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID
            )
        ],
        responses={
            200: openapi.Response(
                description="Payment cancelled successfully",
                schema=PaymentCancellationResponseSerializer
            ),
            400: "Bad Request - Payment cannot be cancelled",
            404: "Payment not found",
            401: "Unauthorized - Authentication required"
        },
        tags=['Payments']
    )
    def post(self, request, payment_id):
        """
        Cancel pending payment.
        
        Steps:
        1. Get payment by ID
        2. Verify user owns the payment
        3. Call PaymentService.cancel_payment()
        4. Return success message
        
        Requirements: 12.3, 12.4
        """
        # Step 1: Get payment by ID
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Step 2: Verify user owns the payment
        if payment.user != request.user:
            return Response({
                'success': False,
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'You do not have permission to access this payment'
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Step 3: Call PaymentService.cancel_payment()
        payment_service = PaymentService()
        success = payment_service.cancel_payment(payment)
        
        # Step 4: Return success message
        if success:
            return Response({
                'success': True,
                'message': 'Payment cancelled successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': f'Payment cannot be cancelled. Current status: {payment.status}'
            }, status=status.HTTP_400_BAD_REQUEST)


class MTNWebhookView(APIView):
    """
    POST /api/v1/payments/webhooks/mtn/
    Handle MTN Mobile Money webhook callbacks.
    """
    permission_classes = [AllowAny]  # Webhooks come from external service
    
    @swagger_auto_schema(
        operation_description="Handle MTN Mobile Money webhook callback",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'referenceId': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_STRING),
                'financialTransactionId': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: "Webhook processed successfully",
            401: "Unauthorized - Invalid signature",
            404: "Payment not found"
        },
        tags=['Payments']
    )
    def post(self, request):
        """
        Process MTN webhook callback.
        
        Steps:
        1. Extract signature from headers
        2. Call PaymentService.process_webhook()
        3. Return appropriate HTTP status
        
        Requirements: 8.1, 8.3, 8.4, 8.7
        """
        # Step 1: Extract signature from headers
        signature = request.META.get('HTTP_X_SIGNATURE', '')
        
        if not signature:
            logger.warning("MTN webhook received without signature")
            return Response({
                'error': 'Missing signature'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Step 2: Call PaymentService.process_webhook()
        payment_service = PaymentService()
        success = payment_service.process_webhook(
            provider='mtn',
            payload=request.data,
            signature=signature
        )
        
        # Step 3: Return appropriate HTTP status
        if success:
            return Response({
                'message': 'Webhook processed successfully'
            }, status=status.HTTP_200_OK)
        else:
            # Check if payment was not found
            transaction_ref = request.data.get('referenceId')
            if transaction_ref:
                try:
                    Payment.objects.get(transaction_reference=transaction_ref)
                    # Payment exists but processing failed (likely signature issue)
                    return Response({
                        'error': 'Webhook processing failed'
                    }, status=status.HTTP_401_UNAUTHORIZED)
                except Payment.DoesNotExist:
                    # Payment not found
                    return Response({
                        'error': 'Payment not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'error': 'Webhook processing failed'
            }, status=status.HTTP_400_BAD_REQUEST)


class MembershipFeeView(APIView):
    """
    GET /api/v1/payments/membership-fee/
    Get current membership fee amount.
    """
    permission_classes = [AllowAny]  # Public endpoint
    
    @swagger_auto_schema(
        operation_description="Get the current membership fee amount",
        responses={
            200: openapi.Response(
                description="Membership fee retrieved successfully",
                schema=MembershipFeeResponseSerializer
            )
        },
        tags=['Payments']
    )
    def get(self, request):
        """
        Get membership fee.
        
        Steps:
        1. Call PaymentService.get_membership_fee()
        2. Return amount and currency
        
        Requirements: 13.1
        """
        # Step 1: Call PaymentService.get_membership_fee()
        payment_service = PaymentService()
        amount = payment_service.get_membership_fee()
        
        # Step 2: Return amount and currency
        return Response({
            'amount': str(amount),
            'currency': 'UGX'
        }, status=status.HTTP_200_OK)
