from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth import get_user_model
from .models import Application
from Documents.models import Document
from .serializers import ApplicationSerializer
from . import services
from notifications.serializers import NotificationSerializer
from authentication.permissions import AllowPublicApplicationSubmission
from drf_yasg.utils import swagger_auto_schema
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


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
    queryset = Application.objects.all().order_by('-submitted_at')
    serializer_class = ApplicationSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowPublicApplicationSubmission]

   
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
       recent_apps = Application.objects.order_by('-submitted_at')[:5]
       serializer = self.get_serializer(recent_apps, many=True)
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
