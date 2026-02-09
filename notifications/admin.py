from django.contrib import admin
from .models import Notification, UserNotification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__email', 'message']
    date_hierarchy = 'created_at'


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'read_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')
