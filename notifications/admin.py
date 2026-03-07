from django.contrib import admin
from .models import Notification, UserNotification, Announcement


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


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'audience', 'channel', 'priority', 'created_by', 'created_at']
    list_filter = ['status', 'audience', 'channel', 'priority', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at', 'sent_at']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'content', 'priority')
        }),
        ('Delivery', {
            'fields': ('audience', 'channel', 'status', 'scheduled_for')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
