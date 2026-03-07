from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone as tz
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Notification, UserNotification, Announcement
from .serializers import (
    NotificationSerializer, UserNotificationSerializer,
    AnnouncementSerializer, AnnouncementCreateSerializer, AnnouncementStatsSerializer,
)
from .announcement_services import send_announcement_email, create_in_app_notifications
from authentication.permissions import IsAdmin

class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notifications.
    - Admins can list all notifications.
    - Users can list their own notifications.
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    @swagger_auto_schema(
        tags=["Notifications"],
        operation_description="List notifications. Admins see all, users see only their own.",
        responses={
            200: openapi.Response(
                description="List of notifications",
                schema=NotificationSerializer(many=True)
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        tags=["Notifications"],
        operation_description="Retrieve a specific notification by ID",
        responses={
            200: openapi.Response(
                description="Notification details",
                schema=NotificationSerializer
            ),
            404: "Notification not found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        tags=["Notifications"],
        operation_description="Create a new notification (admin only)",
        request_body=NotificationSerializer,
        responses={
            201: openapi.Response(
                description="Notification created successfully",
                schema=NotificationSerializer
            )
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        # Skip during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        
        user = self.request.user
        if user and user.is_staff:
            return Notification.objects.all()
        return Notification.objects.filter(user=user) if user else Notification.objects.none()


class UserNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for general user notifications (announcements, system messages, etc.)
    - Users can only see their own notifications
    - Users can mark notifications as read
    - Returns combined notifications from both UserNotification and Notification models
    """
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only see their own notifications"""
        # Return only UserNotification (announcements, system messages)
        # Application-specific Notification model is handled separately
        return UserNotification.objects.filter(user=self.request.user)
    
    @swagger_auto_schema(
        tags=["Notifications"],
        operation_description="List all notifications for the current user. Combines UserNotification (announcements, system messages) and application-specific Notification records.",
        responses={
            200: openapi.Response(
                description="Combined list of all user notifications",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "title": "Welcome to APF",
                            "message": "Your application has been received",
                            "notification_type": "info",
                            "priority": "medium",
                            "is_read": False,
                            "created_at": "2026-03-02T14:27:30.002748+03:00",
                            "read_at": None
                        }
                    ]
                }
            )
        }
    )
    def list(self, request, *args, **kwargs):
        """
        List all notifications for the current user
        Combines UserNotification and application-specific Notification records
        """
        # Get UserNotification records (announcements, system messages)
        user_notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')
        
        # Get application-specific Notification records
        app_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        
        # Serialize UserNotification records
        user_notif_data = UserNotificationSerializer(user_notifications, many=True).data
        
        # Transform application-specific Notification records to match UserNotification format
        app_notif_data = []
        for notif in app_notifications:
            app_notif_data.append({
                'id': notif.id,
                'title': f"Application Update",  # Generic title for app notifications
                'message': notif.message,
                'notification_type': notif.type,
                'priority': 'medium',  # Default priority
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat() if notif.created_at else None,
                'read_at': None,  # Application Notification model doesn't have read_at
            })
        
        # Combine both lists
        combined_notifications = list(user_notif_data) + app_notif_data
        
        # Sort by created_at (most recent first) - both are now ISO strings
        combined_notifications.sort(key=lambda x: x.get('created_at') or '', reverse=True)
        
        print(f"[Notification] List for user {request.user.email}:")
        print(f"  - UserNotification: {len(user_notif_data)}")
        print(f"  - Notification (app-specific): {len(app_notif_data)}")
        print(f"  - Total: {len(combined_notifications)}")
        
        return Response(combined_notifications)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        # Try to find in UserNotification first
        try:
            notification = UserNotification.objects.get(id=pk, user=request.user)
            print(f"[Notification] Marking UserNotification {notification.id} as read for user {request.user.email}")
            print(f"[Notification] Before: is_read={notification.is_read}")
            notification.mark_as_read()
            print(f"[Notification] After: is_read={notification.is_read}, read_at={notification.read_at}")
            serializer = self.get_serializer(notification)
            return Response(serializer.data)
        except UserNotification.DoesNotExist:
            pass
        
        # Try to find in application-specific Notification
        try:
            notification = Notification.objects.get(id=pk, user=request.user)
            print(f"[Notification] Marking application Notification {notification.id} as read for user {request.user.email}")
            print(f"[Notification] Before: is_read={notification.is_read}")
            notification.is_read = True
            notification.save()
            print(f"[Notification] After: is_read={notification.is_read}")
            
            # Return in UserNotification format
            return Response({
                'id': notification.id,
                'title': 'Application Update',
                'message': notification.message,
                'notification_type': notification.type,
                'priority': 'medium',
                'is_read': notification.is_read,
                'created_at': notification.created_at,
                'read_at': None,
            })
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for the current user"""
        from django.utils import timezone
        
        # Count unread before
        user_notif_unread_before = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        app_notif_unread_before = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        print(f"[Notification] Marking all notifications as read for user {request.user.email}")
        print(f"[Notification] Unread before:")
        print(f"  - UserNotification: {user_notif_unread_before}")
        print(f"  - Notification (app-specific): {app_notif_unread_before}")
        
        # Mark UserNotification as read
        user_notif_updated = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Mark application-specific Notification as read
        app_notif_updated = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True
        )
        
        total_updated = user_notif_updated + app_notif_updated
        
        print(f"[Notification] Updated:")
        print(f"  - UserNotification: {user_notif_updated}")
        print(f"  - Notification (app-specific): {app_notif_updated}")
        print(f"  - Total: {total_updated}")
        
        # Verify unread count after
        user_notif_unread_after = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        app_notif_unread_after = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        print(f"[Notification] Unread after:")
        print(f"  - UserNotification: {user_notif_unread_after}")
        print(f"  - Notification (app-specific): {app_notif_unread_after}")
        
        return Response({
            'marked_read': total_updated,
            'user_notifications': user_notif_updated,
            'application_notifications': app_notif_updated
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        # Count UserNotification (announcements, system messages, etc.)
        user_notif_count = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Also count application-specific Notification model
        app_notif_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Total unread count
        total_count = user_notif_count + app_notif_count
        
        print(f"[Notification] Unread count for user {request.user.email}:")
        print(f"  - UserNotification (announcements): {user_notif_count}")
        print(f"  - Notification (application-specific): {app_notif_count}")
        print(f"  - Total: {total_count}")
        
        return Response({
            'unread_count': total_count,
            'user_notifications': user_notif_count,
            'application_notifications': app_notif_count
        })


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing announcements.
    Consolidated from the former AdminNotifications app.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Announcement.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AnnouncementCreateSerializer
        return AnnouncementSerializer
    
    @swagger_auto_schema(tags=["Notifications"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["Notifications"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["Notifications"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["Notifications"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["Notifications"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["Notifications"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Set the created_by field to the current user"""
        announcement = serializer.save(created_by=self.request.user)
        
        # If status is sent, set sent_at timestamp and send notifications
        if announcement.status == 'sent':
            announcement.sent_at = tz.now()
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
            announcement.sent_at = tz.now()
            announcement.save()
            
            # Send notifications
            try:
                send_announcement_email(announcement)
                create_in_app_notifications(announcement)
            except Exception as e:
                print(f"Error sending notifications: {e}")
    
    @swagger_auto_schema(tags=["Notifications"], operation_description="Get announcement statistics")
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
    
    @swagger_auto_schema(tags=["Notifications"], operation_description="Send an announcement immediately")
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
        announcement.sent_at = tz.now()
        announcement.save()
        
        # Send notifications
        try:
            send_announcement_email(announcement)
            create_in_app_notifications(announcement)
        except Exception as e:
            print(f"Error sending notifications: {e}")
        
        serializer = self.get_serializer(announcement)
        return Response(serializer.data)
    
    @swagger_auto_schema(tags=["Notifications"], operation_description="Duplicate an announcement")
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