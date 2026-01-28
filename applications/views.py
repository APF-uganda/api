from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from .models import Application
from .serializers import ApplicationSerializer
from . import services
from notifications.serializers import NotificationSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling membership application submissions.
    Endpoints:
    - POST /api/v1/applications/        (public)
    - GET /api/v1/applications/         (admin only)
    - GET /api/v1/applications/{id}/    (admin only)
    - PATCH /api/v1/applications/{id}/approve/ (admin only)
    - PATCH /api/v1/applications/{id}/reject/  (admin only)
    - PATCH /api/v1/applications/{id}/retry/   (admin only)
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser()]

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