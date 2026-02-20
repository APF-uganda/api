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
        try:
            # Use POST data only to avoid deep-copying file objects in request.data
            data = request.POST.copy()
            if 'document_types' in data:
                data.pop('document_types')

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            # Use serializer.save() so create() handles password hashing.
            application = serializer.save()

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
    
    @action(detail=True, methods=["post"], url_path="submit")
    def submit_application(self, request, pk=None):
        """
        POST /api/applications/{id}/submit/
        Submit application after payment verification.
        
        Requirements: 14.3, 14.4
        """
        try:
            application = self.get_object()
            
            # Check if application has a linked payment
            if not application.current_payment:
                return Response({
                    "success": False,
                    "error": "No payment linked to this application. Please complete payment first."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if payment is completed
            payment = application.current_payment
            if payment.status != 'completed':
                return Response({
                    "success": False,
                    "error": f"Payment is not completed. Current status: {payment.status}",
                    "payment_status": payment.status,
                    "can_retry": payment.can_retry()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update application status to submitted (if needed)
            # The application is already created, so we just verify payment is complete
            application.payment_status = 'success'
            application.save()
            
            response_serializer = self.get_serializer(application)
            return Response({
                "success": True,
                "message": "Application submitted successfully",
                "application": response_serializer.data
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
                "error": "Failed to submit application"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    @action(detail=True, methods=["patch"])
    def retry(self, request, pk=None):
        app = services.retry_application(pk)
        app_serializer = self.get_serializer(app)

        return Response({
            "application": app_serializer.data,
            "message": "Application reset to pending"
        }, status=status.HTTP_200_OK)
    
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
