import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DataError, IntegrityError
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from authentication.email_service_smtp import EmailService
from authentication.permissions import (
    AllowPublicApplicationSubmission,
    IsAdmin,
    IsAuthenticated,
    IsMember,
)
from notifications.serializers import NotificationSerializer

from . import services
from .dashboard_services import (
    get_application_statistics,
    get_recent_payments,
    get_member_dashboard_data,
    get_total_applications,
    get_total_members,
)
from .dashboard_serializers import (
    ApplicationStatisticsSerializer,
    MemberDashboardSerializer,
    TotalApplicationSerializer,
    TotalMemberSerializer,
)
from .models import Application
from .serializers import ApplicationListSerializer, ApplicationSerializer

logger = logging.getLogger(__name__)
User = get_user_model()

APPLICATION_LIST_ONLY_FIELDS = (
    "id",
    "username",
    "email",
    "first_name",
    "last_name",
    "icpau_certificate_number",
    "status",
    "payment_status",
    "submitted_at",
    "updated_at",
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all().order_by('-submitted_at')
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        """Return permissions per action with one consistent policy path."""
        public_actions = {"send_otp", "verify_otp", "check_availability"}

        if self.action == "create":
            permission_classes = [AllowPublicApplicationSubmission]
        elif self.action in public_actions:
            permission_classes = [AllowAny]
        elif self.action == "member_dashboard":
            permission_classes = [IsAuthenticated, IsMember]
        else:
            permission_classes = self.permission_classes

        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path='send-otp')
    def send_otp(self, request):
        from authentication.models import User
        email = request.data.get('email')
        username = request.data.get('user_name', 'Applicant')

        if not email:
            return Response({'message': 'Email is required'}, status=400)

        # Check before sending OTP — fail fast with a clear message
        if Application.objects.filter(email__iexact=email).exclude(status='rejected').exists():
            return Response({
                'message': 'An application with this email already exists. Please use a different email or contact support.'
            }, status=400)

        if User.objects.filter(email__iexact=email, is_active=True).exists():
            return Response({
                'message': 'An account with this email already exists. Please log in instead.'
            }, status=400)

        try:
            # Service returns the signed token (No DB used!)
            token = services.send_registration_otp(email, username)
            
            return Response({
                'status': 'OTP sent',
                'token': token,  # <--- React must save this in state/localStorage
                'message': f'Code sent to {email}'
            }, status=200)
        except Exception as e:
            logger.error(f"Error sending OTP: {str(e)}")
            return Response({'message': 'Failed to send email.'}, status=500)

    @action(detail=False, methods=['post'], url_path='verify-otp')
    def verify_otp(self, request):
        email = request.data.get('email')
        code = request.data.get('verification_code')
        token = request.data.get('token') # <--- React must send this back

        if not token:
            return Response({'message': 'Session token missing. Request a new OTP.'}, status=400)

        if services.verify_registration_otp(email, code, token):
            return Response({
                'status': 'verified', 
                'message': 'Email verified successfully!'
            }, status=200)
        
        return Response({
            'status': 'error',
            'message': 'Invalid or expired verification code.'
        }, status=400)
    
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
            return Application.objects.only(*APPLICATION_LIST_ONLY_FIELDS).order_by('-submitted_at')
        return Application.objects.all().order_by('-submitted_at')

    def _safe_created_application_payload(self, application):
        """
        Build a fallback response payload without touching reverse relations.
        This prevents create() from failing if documents table/state is inconsistent.
        """
        return {
            "id": application.id,
            "username": application.username,
            "email": application.email,
            "first_name": application.first_name,
            "last_name": application.last_name,
            "name": f"{application.first_name} {application.last_name}".strip(),
            "age_range": application.age_range,
            "phone_number": application.phone_number,
            "address": application.address,
            "national_id_number": application.national_id_number,
            "icpau_certificate_number": application.icpau_certificate_number,
            "payment_method": application.payment_method,
            "payment_phone": application.payment_phone,
            "payment_status": application.payment_status,
            "payment_transaction_reference": application.payment_transaction_reference,
            "payment_error_message": application.payment_error_message,
            "payment_amount": application.payment_amount,
            "status": application.status,
            "submitted_at": application.submitted_at,
            "updated_at": application.updated_at,
            "documents": [],
        }

    def _extract_application_data(self, request):
        """Return validated input payload for application creation."""
        content_type = request.content_type or ""
        if content_type.startswith("application/json"):
            data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        else:
            data = request.POST.copy()

        data.pop("document_types", None)
        return data

    def _extract_document_types(self, request):
        """Normalize document_types from multipart or json payloads."""
        if hasattr(request.data, "getlist"):
            return request.data.getlist("document_types")

        document_types = request.data.get("document_types", [])
        if isinstance(document_types, str):
            return [document_types]
        return document_types

    @staticmethod
    def _should_refresh_payment(payment):
        return payment.status in {"pending", "processing"}

    @staticmethod
    def _build_payment_info(payment, include_error_message=False):
        if not payment:
            return None

        data = {
            "id": str(payment.id),
            "status": payment.status,
            "transaction_reference": payment.transaction_reference,
            "provider": payment.provider,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
            "completed_at": payment.completed_at,
            "can_retry": payment.can_retry(),
        }
        if include_error_message:
            data["error_message"] = payment.error_message
        return data

    def _refresh_pending_payment(self, payment):
        if not self._should_refresh_payment(payment):
            return

        from payments.services.payment_service import PaymentService

        PaymentService().check_payment_status(payment)
        payment.refresh_from_db()

    def _application_action_response(self, application, include_notification=False, message=None):
        payload = {"application": self.get_serializer(application).data}

        if include_notification:
            notification = application.notifications.first()
            payload["notification"] = NotificationSerializer(notification).data

        if message:
            payload["message"] = message

        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Applications"],
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
        tags=["Applications"],
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
            data = self._extract_application_data(request)

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            # Use serializer.save() so create() handles password hashing.
            try:
                application = serializer.save()
            except IntegrityError as exc:
                logger.exception("Database integrity error while creating application")
                message = str(exc) if settings.DEBUG else "Application conflicts with existing data."
                return Response(
                    {"errors": {"non_field_errors": [message]}},
                    status=status.HTTP_409_CONFLICT
                )
            except DataError as exc:
                logger.exception("Database data error while creating application")
                message = str(exc) if settings.DEBUG else "Invalid data for one or more fields."
                return Response(
                    {"errors": {"non_field_errors": [message]}},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Handle file uploads (only for multipart/form-data)
            uploaded_files = request.FILES.getlist('documents')
            document_types = self._extract_document_types(request)

            if uploaded_files:
                services.create_application_documents(application, uploaded_files, document_types)

            # Notify admins about the new application
            try:
                from notifications.admin_notification_service import notify_admin_new_application
                notify_admin_new_application(application)
                logger.info(f"[Application] Notified admins about new application from {application.email}")
            except Exception as e:
                logger.warning(f"[Application] Failed to notify admins: {e}")

            try:
                response_serializer = self.get_serializer(application)
                response_data = response_serializer.data
            except Exception:
                logger.exception("Failed to serialize created application; returning safe payload")
                response_data = self._safe_created_application_payload(application)

            return Response(response_data, status=status.HTTP_201_CREATED)
        except ValidationError as exc:
            return Response(
                {"errors": exc.detail},
                status=status.HTTP_409_CONFLICT
            )
        except Exception as exc:
            logger.exception("Failed to create application")
            error_payload = {"message": "Failed to submit application"}
            if settings.DEBUG:
                error_payload["debug"] = str(exc)
            return Response(
                {"error": error_payload},
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
                        "payment_status": "none",
                        "application_status": application.status
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the payment and check its current status
            payment = application.current_payment
            
            # If payment is still pending/processing, check with provider
            if self._should_refresh_payment(payment):
                self._refresh_pending_payment(payment)
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
            
            # Payment is completed - if application is still pending, approve it now.
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

            # Send confirmation email to applicant
            try:
                applicant_email = application.email or (application.user.email if application.user else None)
                if applicant_email:
                    user_name = (
                        application.first_name
                        or (application.user.first_name if application.user else None)
                        or applicant_email.split('@')[0]
                    )
                    submitted_at = timezone.now().strftime('%d %B %Y, %H:%M')
                    EmailService.send_application_confirmation_email(
                        email=applicant_email,
                        user_name=user_name,
                        application_id=application.id,
                        submitted_at=submitted_at,
                    )
            except Exception:
                logger.exception("Failed to send application confirmation email for application %s", application.id)
            
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
                if request.query_params.get('refresh') == 'true' and self._should_refresh_payment(payment):
                    self._refresh_pending_payment(payment)
                    application.refresh_from_db()
                
                payment_info = self._build_payment_info(payment)
            
            return Response({
                "success": True,
                "application": {
                    "id": application.id,
                    "status": application.status,
                    "payment_status": payment_info["status"] if payment_info else "none",
                    "email": application.user.email if application.user else "",
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
        return self._application_action_response(app, include_notification=True)

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
        return self._application_action_response(app, include_notification=True)

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
        return self._application_action_response(app, message="Application reset to pending")
    
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
       recent_apps = Application.objects.only(*APPLICATION_LIST_ONLY_FIELDS).order_by('-submitted_at')[:5]
       # Use the list serializer for consistency
       serializer = ApplicationListSerializer(recent_apps, many=True)
       return Response(serializer.data, status=status.HTTP_200_OK)

    # # @swagger_auto_schema(
    #     method='get',
    #     operation_description="Check if email is available (public endpoint)",
    #     manual_parameters=[
    #         openapi.Parameter('email', openapi.IN_QUERY, description="Email to check", type=openapi.TYPE_STRING),
    #     ],
    #     responses={
    #         200: openapi.Response(
    #             description="Availability status",
    #             examples={
    #                 "application/json": {
    #                     "available": True,
    #                     "field": "email"
    #                 }
    #             }
    #         )
    #     },
    #     tags=['Applications']
    # )
    @swagger_auto_schema(method='get', auto_schema=None)
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
                    "payment_status": "none",
                    "message": "No payment linked to this application"
                }, status=status.HTTP_200_OK)
            
            # Get the linked payment
            payment = application.current_payment
            payment_info = self._build_payment_info(payment, include_error_message=True)
            
            # Return payment details
            return Response({
                "has_payment": True,
                "payment_id": payment_info["id"],
                "payment_status": payment_info["status"],
                "application_payment_status": payment_info["status"],
                "transaction_reference": payment_info["transaction_reference"],
                "provider": payment_info["provider"],
                "amount": payment_info["amount"],
                "currency": payment_info["currency"],
                "created_at": payment_info["created_at"],
                "updated_at": payment_info["updated_at"],
                "completed_at": payment_info["completed_at"],
                "error_message": payment_info["error_message"],
                "can_submit": payment_info["status"] == 'completed',
                "message": self._get_payment_status_message(payment_info["status"])
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

    # ── Dashboard endpoints (consolidated from dashboard app) ──

    @swagger_auto_schema(
        method='get',
        operation_description="Get total number of applications in the system",
        responses={
            200: TotalApplicationSerializer,
        },
        tags=['Applications'],
    )
    @action(detail=False, methods=['get'], url_path='total-applications', permission_classes=[IsAuthenticated, IsAdmin])
    def total_applications(self, request):
        """GET /api/v1/applications/total-applications/ — total applications count."""
        data = {"total_applications": get_total_applications()}
        serializer = TotalApplicationSerializer(data)
        return Response(serializer.data)

    @swagger_auto_schema(
        method='get',
        operation_description="Get total number of members in the system",
        responses={
            200: TotalMemberSerializer,
        },
        tags=['Applications'],
    )
    @action(detail=False, methods=['get'], url_path='total-members', permission_classes=[IsAuthenticated, IsAdmin])
    def total_members(self, request):
        """GET /api/v1/applications/total-members/ — total members count."""
        data = {"total_members": get_total_members()}
        serializer = TotalMemberSerializer(data)
        return Response(serializer.data)

    @swagger_auto_schema(
        method='get',
        operation_description="Get comprehensive application statistics including totals, status breakdown, revenue, and trends",
        responses={
            200: openapi.Response(
                description="Application statistics with trends",
                schema=ApplicationStatisticsSerializer,
            )
        },
        tags=['Applications'],
    )
    @action(detail=False, methods=['get'], url_path='statistics', permission_classes=[IsAuthenticated, IsAdmin])
    def statistics(self, request):
        """GET /api/v1/applications/statistics/ — dashboard stats derived from applications."""
        data = get_application_statistics()
        serializer = ApplicationStatisticsSerializer(data)
        return Response(serializer.data)

    @swagger_auto_schema(
        method='get',
        operation_description="Get recent successful payments for dashboard display",
        manual_parameters=[
            openapi.Parameter('limit', openapi.IN_QUERY, description="Number of recent payments to return (default: 5)", type=openapi.TYPE_INTEGER, default=5),
        ],
        responses={
            200: openapi.Response(description="List of recent payments")
        },
        tags=['Applications'],
    )
    @action(detail=False, methods=['get'], url_path='recent-payments', permission_classes=[IsAuthenticated, IsAdmin])
    def recent_payments(self, request):
        """GET /api/v1/applications/recent-payments/ — recent payments derived from applications."""
        limit = int(request.query_params.get('limit', 5))
        payments = get_recent_payments(limit)
        return Response(payments)

    @swagger_auto_schema(
        method='get',
        operation_description="Search applications and members by name, email, or phone",
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="Search query string", type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: openapi.Response(description="Search results containing applications and members")
        },
        tags=['Applications'],
    )
    @action(detail=False, methods=['get'], url_path='search', permission_classes=[IsAuthenticated, IsAdmin])
    def search(self, request):
        """GET /api/v1/applications/search/ — search applications and members."""
        from django.db.models import Q
        
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'results': []})
        
        results = []
        
        # Search applications
        applications = Application.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(username__icontains=query) |
            Q(phone_number__icontains=query)
        )[:20]
        
        for app in applications:
            results.append({
                'type': 'application',
                'id': app.id,
                'name': f"{app.first_name or ''} {app.last_name or ''}".strip() or app.username or app.email,
                'email': app.email,
                'status': app.status,
                'membership_type': getattr(app, 'membership_category', ''),
                'phone': getattr(app, 'phone_number', ''),
                'created_at': app.submitted_at.isoformat() if app.submitted_at else None,
            })
        
        # Search members (users with role=2)
        members = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).filter(role='2')[:20]
        
        for member in members:
            results.append({
                'type': 'member',
                'id': member.id,
                'name': f"{member.first_name or ''} {member.last_name or ''}".strip() or member.email,
                'email': member.email,
                'status': 'active' if member.is_active else 'inactive',
                'membership_type': getattr(member, 'membership_category', ''),
                'phone': '',
                'created_at': member.created_at.isoformat() if hasattr(member, 'created_at') and member.created_at else None,
            })
        
        return Response({'results': results})

    @swagger_auto_schema(
        method='get',
        operation_description="Get comprehensive dashboard data for authenticated member including profile, documents, activity, and notifications",
        responses={
            200: openapi.Response(
                description="Member dashboard data",
                schema=MemberDashboardSerializer,
            ),
            401: "Authentication required"
        },
        tags=['Applications'],
    )
    @action(detail=False, methods=['get'], url_path='member-dashboard', permission_classes=[IsAuthenticated, IsMember])
    def member_dashboard(self, request):
        """GET /api/v1/applications/member-dashboard/ — member dashboard data."""
        data = get_member_dashboard_data(request.user, request=request)
        serializer = MemberDashboardSerializer(data)
        return Response(serializer.data)
