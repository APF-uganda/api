from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework import serializers
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth import get_user_model
from .models import Application
from Documents.models import Document
from .serializers import ApplicationSerializer, ApplicationListSerializer
from . import services
from notifications.serializers import NotificationSerializer
from authentication.permissions import AllowPublicApplicationSubmission
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling membership application submissions.
    Endpoints:
    - POST /api/applications/ - Submit a new application (public)
    - GET /api/applications/ - List all applications (admin only)
    - GET /api/applications/{id}/ - Retrieve specific application (admin only)
    - PUT/PATCH /api/applications/{id}/ - Update application (admin only)
    - DELETE /api/applications/{id}/ - Delete application (admin only)
    
    Security:
    - Public can submit applications (POST)
    - Only admins can view, update, or delete applications
    - JWT authentication required for admin operations
    
    Requirements: 9.2, 9.5, 10.5
    """
    # Don't use pagination for the main list endpoint to maintain frontend compatibility
    # pagination_class = StandardResultsSetPagination
    queryset = Application.objects.all().order_by('-submitted_at')
    serializer_class = ApplicationSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    # Remove authentication_classes from class level - let DRF handle it via settings
    # authentication_classes = [JWTAuthentication]
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        - Allow unauthenticated POST for public application submission
        - Require admin authentication for all other operations
        """
        if self.action == 'create':
            # Allow anyone to create applications (public submission)
            permission_classes = [AllowPublicApplicationSubmission]
        elif self.action == 'recent' or self.action == 'list':
            # Allow admin users to access recent and full application lists
            from authentication.permissions import IsAuthenticated, IsAdmin
            permission_classes = [IsAuthenticated, IsAdmin]
        else:
            # All other actions (retrieve, update, partial_update, destroy, custom actions) require admin authentication
            from authentication.permissions import IsAuthenticated, IsAdmin
            permission_classes = [IsAuthenticated, IsAdmin]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """
        Use different serializers for different actions to optimize performance
        """
        if self.action == 'list':
            return ApplicationListSerializer
        return ApplicationSerializer

    def get_queryset(self):
        """
        Optimize queryset for different actions
        """
        if self.action == 'list':
            # Optimize the queryset for list view to prevent N+1 queries
            # Only select the fields needed for the list view
            return Application.objects.only(
                'id', 'username', 'email', 'first_name', 'last_name',
                'status', 'payment_status', 'submitted_at', 'updated_at'
            ).order_by('-submitted_at')
        return Application.objects.all().order_by('-submitted_at')
    @swagger_auto_schema(
        tags=["applications"],
        operation_description="List all applications with pagination. Admins see all applications, members see only their own.",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number for pagination",
                type=openapi.TYPE_INTEGER,
                default=1
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Number of items per page (default: 10)",
                type=openapi.TYPE_INTEGER,
                default=10
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by application status",
                type=openapi.TYPE_STRING,
                enum=['pending', 'approved', 'rejected']
            ),
            openapi.Parameter(
                'payment_status',
                openapi.IN_QUERY,
                description="Filter by payment status",
                type=openapi.TYPE_STRING,
                enum=['idle', 'pending', 'completed', 'failed']
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of applications",
                schema=ApplicationListSerializer(many=True),
                examples={
                    "application/json": {
                        "count": 45,
                        "next": "http://64.225.121.230:8000/api/v1/applications/?page=2",
                        "previous": None,
                        "results": [
                            {
                                "id": 45,
                                "username": "Eric",
                                "email": "ericmhwz@gmail.com",
                                "first_name": "Eric",
                                "last_name": "Muhwezi",
                                "name": "Eric Muhwezi",
                                "icpau_certificate_number": "ICPAU/1111/11",
                                "icpaCertNo": "ICPAU/1111/11",
                                "status": "pending",
                                "payment_status": "idle",
                                "submitted_at": "2026-03-02T14:27:30.002748+03:00",
                                "updated_at": "2026-03-02T14:27:30.002788+03:00"
                            }
                        ]
                    }
                }
            )
        }
    )
    def list(self, request, *args, **kwargs):
        """List all applications with pagination"""
        return super().list(request, *args, **kwargs)


    @swagger_auto_schema(
        tags=["applications"],
        operation_description="Retrieve a single application by ID with all details including documents",
        responses={
            200: openapi.Response(
                description="Application details retrieved successfully",
                schema=ApplicationSerializer,
                examples={
                    "application/json": {
                        "id": 1,
                        "username": "Eric",
                        "email": "ericmhwz@gmail.com",
                        "first_name": "Eric",
                        "last_name": "Muhwezi",
                        "name": "Eric Muhwezi",
                        "age_range": "18 – 24",
                        "phone_number": "256761634441",
                        "address": "Muyenga",
                        "national_id_number": "CM01234567890",
                        "icpau_certificate_number": "ICPAU/1111/11",
                        "icpaCertNo": "ICPAU/1111/11",
                        "payment_method": "mtn",
                        "payment_phone": "256761631401",
                        "payment_status": "completed",
                        "payment_amount": "50000.00",
                        "status": "approved",
                        "submitted_at": "2026-03-02T14:27:30.002748+03:00",
                        "updated_at": "2026-03-02T14:27:30.002788+03:00",
                        "documents": []
                    }
                }
            ),
            404: "Application not found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Custom retrieve method with better error handling and logging
        """
        try:
            logger.info(f"Retrieve request for application {kwargs.get('pk')} by user: {request.user}")
            logger.info(f"User authenticated: {request.user.is_authenticated}")
            logger.info(f"User role: {getattr(request.user, 'role', 'N/A')}")
            logger.info(f"Auth header present: {'HTTP_AUTHORIZATION' in request.META}")
            
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving application: {str(e)}", exc_info=True)
            raise



   
    def create(self, request, *args, **kwargs):
        """
        Create a new membership application (public endpoint)
        """
        try:
            # Handle both JSON and form-data
            if request.content_type == 'application/json':
                # For JSON requests, use request.data directly
                data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
                # Remove document_types if present (handled separately)
                if 'document_types' in data:
                    data.pop('document_types')
            else:
                # For form-data requests, use request.POST
                data = request.POST.copy()
                if 'document_types' in data:
                    data.pop('document_types')

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            # Use serializer.save() so create() handles password hashing.
            application = serializer.save()

            # Handle file uploads (only for multipart/form-data)
            uploaded_files = request.FILES.getlist('documents')
            if hasattr(request.data, 'getlist'):
                document_types = request.data.getlist('document_types')
            else:
                document_types = request.data.get('document_types', [])
                if isinstance(document_types, str):
                    document_types = [document_types]

            if uploaded_files:
                services.create_application_documents(application, uploaded_files, document_types)

            response_serializer = self.get_serializer(application)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as exc:
            return Response(
                {"errors": exc.detail},
                status=status.HTTP_409_CONFLICT
            )
        except Exception:
            logger.exception("Failed to create application")
            return Response(
                {"error": {"message": "Failed to submit application"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    create = swagger_auto_schema(
        operation_description="""
        Submit a new membership application (public endpoint - no authentication required).
        
        This endpoint accepts multipart/form-data for file uploads.
        All fields marked as required must be provided.
        
        **Required Fields:**
        - username, email, password_hash, first_name, last_name
        - age_range, phone_number, address
        - payment_method
        
        **Optional Fields:**
        - national_id_number, icpau_certificate_number
        - payment_phone (required if payment_method is 'mtn' or 'airtel')
        - payment_card_* fields (required if payment_method is 'card')
        - documents (file uploads)
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'email', 'password_hash', 'first_name', 'last_name', 
                     'age_range', 'phone_number', 'address', 'payment_method'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Unique username'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='Email address'),
                'password_hash': openapi.Schema(type=openapi.TYPE_STRING, format='password', description='Password (will be hashed)'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
                'age_range': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['18-25', '26-35', '36-45', '46-55', '56+'],
                    description='Age range'
                ),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number (format: +256XXXXXXXXX)'),
                'address': openapi.Schema(type=openapi.TYPE_STRING, description='Physical address'),
                'national_id_number': openapi.Schema(type=openapi.TYPE_STRING, description='National ID number (optional)'),
                'icpau_certificate_number': openapi.Schema(type=openapi.TYPE_STRING, description='ICPAU certificate number (optional)'),
                'payment_method': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['mtn', 'airtel', 'card'],
                    description='Payment method'
                ),
                'payment_phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone for mobile money (required for mtn/airtel)'),
                'payment_card_number': openapi.Schema(type=openapi.TYPE_STRING, description='Card number (required for card payment)'),
                'payment_card_expiry': openapi.Schema(type=openapi.TYPE_STRING, description='Card expiry MM/YY (required for card)'),
                'payment_card_cvv': openapi.Schema(type=openapi.TYPE_STRING, description='Card CVV (required for card)'),
                'payment_cardholder_name': openapi.Schema(type=openapi.TYPE_STRING, description='Cardholder name (required for card)'),
            },
        ),
        responses={
            201: openapi.Response(
                description="Application created successfully",
                schema=ApplicationSerializer
            ),
            409: openapi.Response(
                description="Validation error - missing or invalid fields",
                examples={
                    "application/json": {
                        "errors": {
                            "email": ["This field is required."],
                            "phone_number": ["Invalid phone number format."]
                        }
                    }
                }
            ),
            500: "Internal server error"
        },
        tags=['Applications']
    )(create)
    
    @swagger_auto_schema(
        method='post',
        operation_description="Submit application after payment is completed",
        responses={
            200: openapi.Response(
                description="Application submitted successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Application submitted successfully",
                        "application": {}
                    }
                }
            ),
            400: "Payment not completed or application already submitted",
            404: "Application not found"
        },
        tags=['Applications']
    )
    @action(detail=True, methods=["post"], url_path="submit")
    def submit_application(self, request, pk=None):
        """
        POST /api/applications/{id}/submit/
        Submit application after payment verification.
        
        NOTE: With auto-approval enabled, this endpoint mainly serves to:
        1. Verify payment is completed
        2. Trigger status check if needed
        3. Return current application status
        
        Requirements: 14.3, 14.4
        """
        try:
            application = self.get_object()
            
            # Check if application has a linked payment
            if not application.current_payment:
                return Response({
                    "success": False,
                    "error": "No payment linked to this application. Please complete payment first.",
                    "debug": {
                        "application_id": application.id,
                        "payment_status": application.payment_status,
                        "application_status": application.status
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the payment and check its current status
            payment = application.current_payment
            
            # If payment is still pending/processing, check with provider
            if payment.status in ['pending', 'processing']:
                from payments.services.payment_service import PaymentService
                payment_service = PaymentService()
                current_status, message = payment_service.check_payment_status(payment)
                
                # Refresh payment from DB after status check
                payment.refresh_from_db()
                application.refresh_from_db()
            
            # Check if payment is completed
            if payment.status != 'completed':
                return Response({
                    "success": False,
                    "error": f"Payment is not completed. Current status: {payment.status}",
                    "payment_status": payment.status,
                    "application_status": application.status,
                    "can_retry": payment.can_retry(),
                    "debug": {
                        "payment_id": str(payment.id),
                        "transaction_reference": payment.transaction_reference,
                        "provider": payment.provider
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Payment is completed - application should already be approved by auto-approval
            # But update payment_status just in case
            if application.payment_status != 'success':
                application.payment_status = 'success'
                application.save()
            
            # If application is still pending (auto-approval didn't trigger), approve it now
            if application.status == 'pending':
                application.status = 'approved'
                application.save()
                logger.info(
                    f"Application manually approved via submit endpoint",
                    extra={
                        "application_id": application.id,
                        "payment_id": str(payment.id)
                    }
                )
            
            response_serializer = self.get_serializer(application)
            return Response({
                "success": True,
                "message": "Application submitted successfully" if application.status == 'approved' else "Application is under review",
                "application": response_serializer.data,
                "status": application.status
            }, status=status.HTTP_200_OK)
            
        except Application.DoesNotExist:
            return Response({
                "success": False,
                "error": "Application not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Failed to submit application")
            return Response({
                "success": False,
                "error": "Failed to submit application",
                "debug": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Check application status and payment information",
        responses={
            200: openapi.Response(
                description="Application status retrieved",
                examples={
                    "application/json": {
                        "application_id": 1,
                        "status": "pending",
                        "payment_status": "completed",
                        "message": "Application is pending review"
                    }
                }
            ),
            404: "Application not found"
        },
        tags=['Applications']
    )
    @action(detail=True, methods=["get"], url_path="check-status")
    def check_application_status(self, request, pk=None):
        """
        GET /api/applications/{id}/check-status/
        Check application and payment status.
        
        Returns detailed status information for debugging.
        """
        try:
            application = self.get_object()
            
            payment_info = None
            if application.current_payment:
                payment = application.current_payment
                
                # Optionally trigger a fresh status check
                if request.query_params.get('refresh') == 'true' and payment.status in ['pending', 'processing']:
                    from payments.services.payment_service import PaymentService
                    payment_service = PaymentService()
                    payment_service.check_payment_status(payment)
                    payment.refresh_from_db()
                    application.refresh_from_db()
                
                payment_info = {
                    "id": str(payment.id),
                    "status": payment.status,
                    "transaction_reference": payment.transaction_reference,
                    "provider": payment.provider,
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                    "created_at": payment.created_at,
                    "updated_at": payment.updated_at,
                    "completed_at": payment.completed_at,
                    "can_retry": payment.can_retry()
                }
            
            return Response({
                "success": True,
                "application": {
                    "id": application.id,
                    "status": application.status,
                    "payment_status": application.payment_status,
                    "email": application.email,
                    "submitted_at": application.submitted_at,
                    "updated_at": application.updated_at
                },
                "payment": payment_info,
                "is_ready_to_submit": payment_info and payment_info["status"] == "completed",
                "message": self._get_status_message(application, payment_info)
            }, status=status.HTTP_200_OK)
            
        except Application.DoesNotExist:
            return Response({
                "success": False,
                "error": "Application not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Failed to check application status")
            return Response({
                "success": False,
                "error": "Failed to check status",
                "debug": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_status_message(self, application, payment_info):
        """Helper to generate user-friendly status message"""
        if not payment_info:
            return "No payment found. Please initiate payment."
        
        if payment_info["status"] == "completed":
            if application.status == "approved":
                return "Application approved! Your account has been created."
            elif application.status == "pending":
                return "Payment completed. Application is being processed."
            else:
                return f"Application status: {application.status}"
        elif payment_info["status"] in ["pending", "processing"]:
            return "Payment is being processed. Please check your phone to approve the transaction."
        elif payment_info["status"] == "failed":
            return "Payment failed. Please try again."
        else:
            return f"Payment status: {payment_info['status']}"

    @swagger_auto_schema(
        method='patch',
        operation_description="Approve an application (admin only)",
        responses={
            200: openapi.Response(
                description="Application approved",
                schema=ApplicationSerializer
            ),
            404: "Application not found"
        },
        tags=['Applications']
    )
    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        app = services.approve_application(pk)
        app_serializer = self.get_serializer(app)

        # Get the latest notification for this application
        notification = app.notifications.first()
        notif_serializer = NotificationSerializer(notification)

        return Response({
            "application": app_serializer.data,
            "notification": notif_serializer.data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='patch',
        operation_description="Reject an application (admin only)",
        responses={
            200: openapi.Response(
                description="Application rejected",
                schema=ApplicationSerializer
            ),
            404: "Application not found"
        },
        tags=['Applications']
    )
    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        app = services.reject_application(pk)
        app_serializer = self.get_serializer(app)

        notification = app.notifications.first()
        notif_serializer = NotificationSerializer(notification)

        return Response({
            "application": app_serializer.data,
            "notification": notif_serializer.data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='patch',
        operation_description="Retry a failed application",
        responses={
            200: openapi.Response(
                description="Application retry initiated",
                schema=ApplicationSerializer
            ),
            404: "Application not found"
        },
        tags=['Applications']
    )
    @action(detail=True, methods=["patch"])
    def retry(self, request, pk=None):
        app = services.retry_application(pk)
        app_serializer = self.get_serializer(app)

        return Response({
            "application": app_serializer.data,
            "message": "Application reset to pending"
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get recent applications (admin only)",
        manual_parameters=[
            openapi.Parameter('limit', openapi.IN_QUERY, description="Number of applications to return", type=openapi.TYPE_INTEGER, default=10)
        ],
        responses={
            200: openapi.Response(
                description="List of recent applications",
                schema=ApplicationListSerializer(many=True)
            )
        },
        tags=['Applications']
    )
    @action(detail=False, methods=["get"], url_path="recent")
    def recent(self, request):
       """
       Return recent applications for dashboard
       """
       recent_apps = Application.objects.only(
           'id', 'username', 'email', 'first_name', 'last_name',
           'status', 'payment_status', 'submitted_at', 'updated_at'
       ).order_by('-submitted_at')[:5]
       # Use the list serializer for consistency
       serializer = ApplicationListSerializer(recent_apps, many=True)
       return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='get',
        operation_description="Check if email or username is available (public endpoint)",
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, description="Email to check", type=openapi.TYPE_STRING),
            openapi.Parameter('username', openapi.IN_QUERY, description="Username to check", type=openapi.TYPE_STRING)
        ],
        responses={
            200: openapi.Response(
                description="Availability status",
                examples={
                    "application/json": {
                        "available": True,
                        "field": "email"
                    }
                }
            )
        },
        tags=['Applications']
    )
    @action(detail=False, methods=["get"], url_path="check-availability", permission_classes=[AllowAny])
    def check_availability(self, request):
        email = (request.query_params.get('email') or '').strip().lower()
        username = (request.query_params.get('username') or '').strip()

        email_exists = False
        username_exists = False

        if email:
            email_exists = (
                Application.objects.filter(email__iexact=email).exclude(status='rejected').exists() or
                User.objects.filter(email__iexact=email, is_active=True).exists()
            )

        if username:
            username_exists = Application.objects.filter(username__iexact=username).exclude(status='rejected').exists()

        return Response({
            "email_available": not email_exists,
            "username_available": not username_exists
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='get',
        operation_description="Get payment status for an application",
        responses={
            200: openapi.Response(
                description="Payment status information",
                examples={
                    "application/json": {
                        "payment_status": "completed",
                        "payment_method": "mtn",
                        "amount": "50000.00"
                    }
                }
            ),
            404: "Application not found"
        },
        tags=['Applications']
    )
    @action(detail=True, methods=["get"], url_path="payment-status")
    def payment_status(self, request, pk=None):
        """
        GET /api/applications/{id}/payment-status/
        Return payment status for application.
        
        Requirements: 14.3, 14.4
        """
        try:
            application = self.get_object()
            
            # Check if application has a linked payment
            if not application.current_payment:
                return Response({
                    "has_payment": False,
                    "payment_status": application.payment_status,
                    "message": "No payment linked to this application"
                }, status=status.HTTP_200_OK)
            
            # Get the linked payment
            payment = application.current_payment
            
            # Return payment details
            return Response({
                "has_payment": True,
                "payment_id": str(payment.id),
                "payment_status": payment.status,
                "application_payment_status": application.payment_status,
                "transaction_reference": payment.transaction_reference,
                "provider": payment.provider,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "created_at": payment.created_at,
                "updated_at": payment.updated_at,
                "completed_at": payment.completed_at,
                "error_message": payment.error_message,
                "can_submit": payment.status == 'completed',
                "message": self._get_payment_status_message(payment.status)
            }, status=status.HTTP_200_OK)
            
        except Application.DoesNotExist:
            return Response({
                "error": "Application not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Failed to get payment status for application")
            return Response({
                "error": "Failed to retrieve payment status"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_payment_status_message(self, status):
        """Get user-friendly message for payment status."""
        messages = {
            'pending': 'Payment is pending. Please approve on your phone.',
            'processing': 'Payment is being processed.',
            'completed': 'Payment completed successfully.',
            'failed': 'Payment failed. Please try again.',
            'timeout': 'Payment verification timed out. Please try again.',
            'cancelled': 'Payment was cancelled.'
        }
        return messages.get(status, 'Unknown payment status')
