from rest_framework import serializers
from .models import ContactMessage

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at', 'is_read', 'reply', 'replied_at']
        read_only_fields = ['id', 'created_at', 'is_read', 'reply', 'replied_at']


class ContactReplySerializer(serializers.Serializer):
    reply = serializers.CharField(required=True, min_length=1)
