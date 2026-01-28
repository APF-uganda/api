from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import Application, Document
from .serializers import ApplicationSerializer
from . import services
from notifications.serializers import NotificationSerializer
from authentication.permissions import AllowPublicApplicationSubmission


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
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowPublicApplicationSubmission]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_files = request.FILES.getlist('documents')
        application = services.create_application(serializer.validated_data, uploaded_files)

        response_serializer = self.get_serializer(application)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

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