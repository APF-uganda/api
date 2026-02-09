from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import Notification, UserNotification
from .serializers import NotificationSerializer, UserNotificationSerializer

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

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Notification.objects.all()
        return Notification.objects.filter(user=user)


class UserNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for general user notifications (announcements, system messages, etc.)
    - Users can only see their own notifications
    - Users can mark notifications as read
    """
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only see their own notifications"""
        return UserNotification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for the current user"""
        from django.utils import timezone
        updated = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'marked_read': updated})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})