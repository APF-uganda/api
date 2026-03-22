from rest_framework import serializers
from authentication.models import User, UserRole
from Documents.models import MemberDocument
from .models import MembershipStatus, DocumentStatus, SuspendedMember, ProcessedDocument, MembershipInvoice, InvoicePaymentLink, AdminNote


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



# Membership Invoice Serializers

class MembershipInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for membership invoices"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = MembershipInvoice
        fields = [
            'id',
            'invoice_number',
            'user_email',
            'user_name',
            'invoice_date',
            'due_date',
            'period_start',
            'period_end',
            'base_amount',
            'previous_balance',
            'discount',
            'total_amount',
            'amount_paid',
            'balance_due',
            'status',
            'email_sent',
            'email_sent_at',
            'created_at',
            'updated_at',
            'paid_at',
        ]
        read_only_fields = ['balance_due', 'created_at', 'updated_at', 'paid_at']


class InvoicePaymentLinkSerializer(serializers.ModelSerializer):
    """Serializer for invoice payment links"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    payment_reference = serializers.CharField(source='payment.transaction_reference', read_only=True)
    
    class Meta:
        model = InvoicePaymentLink
        fields = [
            'id',
            'invoice_number',
            'payment_reference',
            'amount',
            'created_at',
        ]
        read_only_fields = ['created_at']


class AdminNoteSerializer(serializers.ModelSerializer):
    """Serializer for admin notes on member records"""
    admin_name = serializers.SerializerMethodField()
    admin_email = serializers.SerializerMethodField()
    member_name = serializers.SerializerMethodField()
    member_email = serializers.EmailField(source='member.email', read_only=True)
    
    class Meta:
        model = AdminNote
        fields = [
            'id',
            'member',
            'member_name',
            'member_email',
            'admin',
            'admin_name',
            'admin_email',
            'note_text',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'admin', 'created_at', 'updated_at']
    
    def get_admin_name(self, obj):
        return obj.admin.full_name if obj.admin else 'Unknown'
    
    def get_admin_email(self, obj):
        return obj.admin.email if obj.admin else 'Unknown'
    
    def get_member_name(self, obj):
        return obj.member.full_name


class CreateAdminNoteSerializer(serializers.ModelSerializer):
    """Serializer for creating admin notes"""
    
    class Meta:
        model = AdminNote
        fields = ['note_text']
    
    def validate_note_text(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Note text cannot be empty")
        return value.strip()
