from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Announcement
from .serializers import (
    AnnouncementSerializer,
    AnnouncementCreateSerializer,
    AnnouncementStatsSerializer
)
from authentication.permissions import IsAdmin
from .services import send_announcement_email, create_in_app_notifications


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing announcements
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Announcement.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AnnouncementCreateSerializer
        return AnnouncementSerializer
    
    @swagger_auto_schema(tags=["admin-notifications"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["admin-notifications"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["admin-notifications"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["admin-notifications"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["admin-notifications"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["admin-notifications"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AnnouncementCreateSerializer
        return AnnouncementSerializer
    
    def perform_create(self, serializer):
        """Set the created_by field to the current user"""
        announcement = serializer.save(created_by=self.request.user)
        
        # If status is sent, set sent_at timestamp and send notifications
        if announcement.status == 'sent':
            announcement.sent_at = timezone.now()
            announcement.save()
            
            # Send notifications
            try:
                send_announcement_email(announcement)
                create_in_app_notifications(announcement)
            except Exception as e:
                print(f"Error sending notifications: {e}")
    
    def perform_update(self, serializer):
        """Update sent_at when status changes to sent"""
        announcement = serializer.save()
        
        # If status changed to sent, set sent_at timestamp and send notifications
        if announcement.status == 'sent' and not announcement.sent_at:
            announcement.sent_at = timezone.now()
            announcement.save()
            
            # Send notifications
            try:
                send_announcement_email(announcement)
                create_in_app_notifications(announcement)
            except Exception as e:
                print(f"Error sending notifications: {e}")
    
    @swagger_auto_schema(tags=["admin-notifications"], operation_description="Get announcement statistics")
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get announcement statistics"""
        total = Announcement.objects.count()
        draft = Announcement.objects.filter(status='draft').count()
        scheduled = Announcement.objects.filter(status='scheduled').count()
        sent = Announcement.objects.filter(status='sent').count()
        
        stats_data = {
            'total': total,
            'draft': draft,
            'scheduled': scheduled,
            'sent': sent
        }
        
        serializer = AnnouncementStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @swagger_auto_schema(tags=["admin-notifications"], operation_description="Send an announcement immediately")
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send an announcement immediately"""
        announcement = self.get_object()
        
        if announcement.status == 'sent':
            return Response(
                {'error': 'Announcement has already been sent'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        announcement.status = 'sent'
        announcement.sent_at = timezone.now()
        announcement.save()
        
        # Send notifications
        try:
            send_announcement_email(announcement)
            create_in_app_notifications(announcement)
        except Exception as e:
            print(f"Error sending notifications: {e}")
        
        serializer = self.get_serializer(announcement)
        return Response(serializer.data)
    
    @swagger_auto_schema(tags=["admin-notifications"], operation_description="Duplicate an announcement")
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate an announcement"""
        announcement = self.get_object()
        
        # Create a copy
        new_announcement = Announcement.objects.create(
            title=f"{announcement.title} (Copy)",
            content=announcement.content,
            audience=announcement.audience,
            channel=announcement.channel,
            status='draft',
            created_by=request.user,
            priority=announcement.priority
        )
        
        serializer = self.get_serializer(new_announcement)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        """Filter announcements based on query parameters"""
        queryset = Announcement.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by audience
        audience_filter = self.request.query_params.get('audience', None)
        if audience_filter:
            queryset = queryset.filter(audience=audience_filter)
        
        # Filter by channel
        channel_filter = self.request.query_params.get('channel', None)
        if channel_filter:
            queryset = queryset.filter(channel=channel_filter)
        
        # Search by title or content
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        return queryset
