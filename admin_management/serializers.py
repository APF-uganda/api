from rest_framework import serializers
from authentication.models import User, UserRole
from Documents.models import MemberDocument
from .models import MembershipStatus, DocumentStatus, SuspendedMember, ProcessedDocument


class AdminMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for admin to view member details
    """
    full_name = serializers.SerializerMethodField()
    membership_status = serializers.SerializerMethodField()
    subscription_due_date = serializers.DateField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'phone_number', 
            'membership_status', 'subscription_due_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_full_name(self, obj):
        return obj.full_name
    
    def get_membership_status(self, obj):
        # Check if user is suspended by checking if they're inactive or have an active suspension record
        try:
            if not obj.is_active:
                return MembershipStatus.SUSPENDED
            # Also check if there's a suspension record without reactivation
            if hasattr(obj, 'suspension_record') and obj.suspension_record.reactivated_at is None:
                return MembershipStatus.SUSPENDED
            return MembershipStatus.ACTIVE
        except:
            return MembershipStatus.ACTIVE if obj.is_active else MembershipStatus.SUSPENDED


class SuspendMemberSerializer(serializers.Serializer):
    """
    Serializer for suspending a member
    """
    reason = serializers.CharField(
        max_length=500,
        help_text="Reason for suspending the member"
    )
    
    class Meta:
        fields = ['reason']


class ReactivateMemberSerializer(serializers.Serializer):
    """
    Serializer for reactivating a member
    """
    # No fields needed for reactivation
    
    class Meta:
        fields = []


class AdminDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for admin to view document details
    """
    member = serializers.SerializerMethodField()
    document_type = serializers.CharField(read_only=True)
    file_url = serializers.CharField(source='file.url', read_only=True)
    uploaded_at = serializers.DateTimeField(source='uploaded_at', read_only=True)
    status = serializers.ChoiceField(
        choices=DocumentStatus.choices,
        required=False
    )
    
    class Meta:
        model = MemberDocument
        fields = [
            'id', 'member', 'document_type', 'file_url', 
            'uploaded_at', 'status'
        ]
        read_only_fields = ['id', 'member', 'file_url', 'uploaded_at']
    
    def get_member(self, obj):
        return {
            'id': obj.user.id,
            'full_name': obj.user.full_name,
            'email': obj.user.email
        }


class ApproveDocumentSerializer(serializers.Serializer):
    """
    Serializer for approving a document
    """
    # No fields needed for approval
    
    class Meta:
        fields = []


class RejectDocumentSerializer(serializers.Serializer):
    """
    Serializer for rejecting a document
    """
    reason = serializers.CharField(
        max_length=500,
        help_text="Reason for rejecting the document"
    )
    
    class Meta:
        fields = ['reason']