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
    MembershipFeeResponseSerializer,
    PaymentHistorySerializer
)

logger = logging.getLogger(__name__)


class PaymentInitiationView(APIView):
    """
    POST /api/v1/payments/initiate/
    Initiate a mobile money payment.
    
    This endpoint supports both authenticated and unauthenticated requests:
    - Authenticated: For logged-in members making subscription payments
    - Unauthenticated: For new users making registration payments
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]  # Allow both authenticated and unauthenticated requests
    
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
        
        Supports both authenticated and unauthenticated requests:
        - Authenticated: user=request.user (for member subscription payments)
        - Unauthenticated: user=None (for registration payments)
        
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
        
        # Get user if authenticated, None otherwise
        user = request.user if hasattr(request, 'user') and request.user and request.user.is_authenticated else None
        
        # Step 3: Call PaymentService.initiate_payment()
        success, payment, message = payment_service.initiate_payment(
            user=user,
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
    Check payment status using hybrid webhook-first with polling fallback.
    
    Supports both authenticated and unauthenticated requests to allow
    status checking for registration payments.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]  # Allow both authenticated and unauthenticated requests
    
    @swagger_auto_schema(
        operation_description="Check the current status of a payment (webhook-first with polling fallback)",
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
        Check payment status using hybrid approach.
        
        Steps:
        1. Get payment by ID
        2. Verify user owns the payment (if authenticated)
        3. Call HybridPaymentService.check_payment_status_hybrid()
        4. Return current status and message
        
        Uses webhook-first approach with automatic polling fallback.
        
        Requirements: 1.6, 4.2
        """
        # Step 1: Get payment by ID
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Step 2: Verify user owns the payment (if authenticated)
        # For authenticated requests, verify ownership
        # For unauthenticated requests (registration), allow access
        if request.user and request.user.is_authenticated:
            if payment.user != request.user:
                return Response({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'You do not have permission to access this payment'
                    }
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Step 3: Call HybridPaymentService.check_payment_status_hybrid()
        from .services.hybrid_payment_service import HybridPaymentService
        payment_service = HybridPaymentService()
        current_status, message = payment_service.check_payment_status_hybrid(payment)
        
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
    
    Supports both authenticated and unauthenticated requests to allow
    retrying registration payments.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]  # Allow both authenticated and unauthenticated requests
    
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
        2. Verify user owns the payment (if authenticated)
        3. Call PaymentService.retry_payment()
        4. Return new payment ID
        
        Requirements: 12.1, 12.2
        """
        # Step 1: Get payment by ID
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Step 2: Verify user owns the payment (if authenticated)
        # For authenticated requests, verify ownership
        # For unauthenticated requests (registration), allow access
        if request.user and request.user.is_authenticated:
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
    
    Supports both authenticated and unauthenticated requests to allow
    canceling registration payments.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]  # Allow both authenticated and unauthenticated requests
    
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
        2. Verify user owns the payment (if authenticated)
        3. Call PaymentService.cancel_payment()
        4. Return success message
        
        Requirements: 12.3, 12.4
        """
        # Step 1: Get payment by ID
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Step 2: Verify user owns the payment (if authenticated)
        # For authenticated requests, verify ownership
        # For unauthenticated requests (registration), allow access
        if request.user and request.user.is_authenticated:
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


class AirtelWebhookView(APIView):
    """
    POST /api/v1/payments/webhooks/airtel/
    Handle Airtel Money webhook callbacks.
    """
    permission_classes = [AllowAny]  # Webhooks come from external service
    
    @swagger_auto_schema(
        operation_description="Handle Airtel Money webhook callback",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'transaction': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
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
        Process Airtel webhook callback.
        
        Steps:
        1. Extract signature from headers
        2. Call PaymentService.process_webhook()
        3. Return appropriate HTTP status
        
        Requirements: 8.2, 8.3, 8.4, 8.7
        """
        # Step 1: Extract signature from headers
        signature = request.META.get('HTTP_X_SIGNATURE', '')
        
        if not signature:
            logger.warning("Airtel webhook received without signature")
            return Response({
                'error': 'Missing signature'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Step 2: Call PaymentService.process_webhook()
        payment_service = PaymentService()
        success = payment_service.process_webhook(
            provider='airtel',
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
            transaction_data = request.data.get('transaction', {})
            transaction_id = transaction_data.get('id')
            
            if transaction_id:
                try:
                    Payment.objects.get(transaction_reference=transaction_id)
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



class AdminTransactionHistoryView(APIView):
    """
    GET /api/v1/payments/admin/transactions/
    Get all payment transactions for admin review.
    Supports filtering by status, provider, and date range.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=["payments-admin"],
        operation_description="Get all payment transactions with filtering options",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by status (pending, processing, completed, failed, timeout, cancelled)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'provider',
                openapi.IN_QUERY,
                description="Filter by provider (mtn, airtel)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Filter by start date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format='date'
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="Filter by end date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format='date'
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Search by transaction reference or user email",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                'Success',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            ),
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required'
        }
    )
    def get(self, request):
        """Get all transactions with optional filtering."""
        from .serializers import AdminTransactionSerializer
        from django.db.models import Q
        from datetime import datetime
        
        # Check if user is admin
        if not (request.user.is_authenticated and request.user.role == '1'):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Start with all payments
        queryset = Payment.objects.select_related('user', 'application').all()
        
        # Apply status filter
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param.lower())
        
        # Apply provider filter
        provider_param = request.query_params.get('provider')
        if provider_param:
            queryset = queryset.filter(provider=provider_param.lower())
        
        # Apply date range filter
        start_date = request.query_params.get('start_date')
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__gte=start_datetime)
            except ValueError:
                pass
        
        end_date = request.query_params.get('end_date')
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__lte=end_datetime)
            except ValueError:
                pass
        
        # Apply search filter
        search_param = request.query_params.get('search')
        if search_param:
            queryset = queryset.filter(
                Q(transaction_reference__icontains=search_param) |
                Q(user__email__icontains=search_param) |
                Q(provider_transaction_id__icontains=search_param)
            )
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        serializer = AdminTransactionSerializer(queryset, many=True)
        
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class AdminRevenueStatsView(APIView):
    """
    GET /api/v1/payments/admin/revenue/
    Get revenue statistics for admin dashboard.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=["payments-admin"],
        operation_description="Get revenue statistics including total revenue, transaction counts by status and provider",
        manual_parameters=[
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Filter by start date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format='date'
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="Filter by end date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format='date'
            ),
        ],
        responses={
            200: 'Success',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required'
        }
    )
    def get(self, request):
        """Get revenue statistics."""
        from .serializers import TransactionRevenueSerializer
        from django.db.models import Sum, Count, Q
        from datetime import datetime
        from decimal import Decimal
        
        # Check if user is admin
        if not (request.user.is_authenticated and request.user.role == '1'):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Start with all payments
        queryset = Payment.objects.all()
        
        # Apply date range filter
        start_date = request.query_params.get('start_date')
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__gte=start_datetime)
            except ValueError:
                pass
        
        end_date = request.query_params.get('end_date')
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__lte=end_datetime)
            except ValueError:
                pass
        
        # Calculate statistics
        total_transactions = queryset.count()
        completed_transactions = queryset.filter(status=Payment.STATUS_COMPLETED).count()
        pending_transactions = queryset.filter(
            status__in=[Payment.STATUS_PENDING, Payment.STATUS_PROCESSING]
        ).count()
        failed_transactions = queryset.filter(
            status__in=[Payment.STATUS_FAILED, Payment.STATUS_TIMEOUT, Payment.STATUS_CANCELLED]
        ).count()
        
        # Calculate revenue (only completed transactions)
        completed_payments = queryset.filter(status=Payment.STATUS_COMPLETED)
        total_revenue = completed_payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        mtn_revenue = completed_payments.filter(provider=Payment.PROVIDER_MTN).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        airtel_revenue = completed_payments.filter(provider=Payment.PROVIDER_AIRTEL).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        data = {
            'total_revenue': total_revenue,
            'total_transactions': total_transactions,
            'completed_transactions': completed_transactions,
            'pending_transactions': pending_transactions,
            'failed_transactions': failed_transactions,
            'mtn_revenue': mtn_revenue,
            'airtel_revenue': airtel_revenue,
            'currency': 'UGX'
        }
        
        serializer = TransactionRevenueSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)



class PaymentHistoryView(APIView):
    """
    GET /api/v1/payments/history/
    Get payment history for the authenticated user.
    
    Supports optional query parameters:
    - status: Filter by payment status (pending, completed, failed, etc.)
    - limit: Number of results to return (default 20, max 100)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get payment history for the authenticated user",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by payment status",
                type=openapi.TYPE_STRING,
                enum=['pending', 'processing', 'completed', 'failed', 'timeout', 'cancelled'],
                required=False
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Number of results (default 20, max 100)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Payment history retrieved successfully",
                schema=PaymentHistorySerializer(many=True)
            ),
            401: "Unauthorized - Authentication required"
        },
        tags=['Payments']
    )
    def get(self, request):
        """
        Get payment history for the current user.
        
        Steps:
        1. Get payments for authenticated user
        2. Apply optional filters
        3. Serialize and return
        """
        # Step 1: Get payments for authenticated user
        payments = Payment.objects.filter(user=request.user).order_by('-created_at')
        
        # Step 2: Apply optional filters
        status_filter = request.query_params.get('status')
        if status_filter:
            payments = payments.filter(status=status_filter)
        
        # Apply limit
        try:
            limit = int(request.query_params.get('limit', 20))
            limit = min(max(limit, 1), 100)
        except (ValueError, TypeError):
            limit = 20
        
        payments = payments[:limit]
        
        # Step 3: Serialize and return
        serializer = PaymentHistorySerializer(payments, many=True)
        return Response({
            'success': True,
            'count': len(serializer.data),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
