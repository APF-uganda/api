from django.contrib import admin
from .models import Announcement


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
