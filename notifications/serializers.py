from rest_framework import serializers
from .models import Notification, UserNotification, Announcement

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = [
            'id', 'title', 'message', 'notification_type', 'priority',
            'is_read', 'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'audience', 'channel', 'status',
            'created_by', 'created_by_name', 'created_by_email',
            'created_at', 'updated_at', 'scheduled_for', 'sent_at', 'priority'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'sent_at']
    
    def get_created_by_name(self, obj):
        if hasattr(obj.created_by, 'full_name') and obj.created_by.full_name:
            return obj.created_by.full_name
        return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
    
    def get_created_by_email(self, obj):
        return obj.created_by.email


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'audience', 'channel', 'status',
            'scheduled_for', 'priority'
        ]
    
    def validate(self, data):
        # If status is scheduled, scheduled_for must be provided
        if data.get('status') == 'scheduled' and not data.get('scheduled_for'):
            raise serializers.ValidationError({
                'scheduled_for': 'Scheduled date is required for scheduled announcements.'
            })
        return data


class AnnouncementStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    draft = serializers.IntegerField()
    scheduled = serializers.IntegerField()
    sent = serializers.IntegerField()