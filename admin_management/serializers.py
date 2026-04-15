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
    has_documents = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    last_document_upload = serializers.SerializerMethodField()
    renewal_status = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'phone_number',
            'membership_status', 'subscription_due_date', 'created_at',
            'has_documents', 'document_count', 'last_document_upload',
            'email_verified', 'must_change_password', 'renewal_status',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_full_name(self, obj):
        return obj.full_name

    def get_renewal_status(self, obj):
        """
        Renewal logic:
        - Due date is always March 31st of the current/next year
        - If joined before April 1st of current year → due date is March 31st this year
          → if that date has passed and no verified payment → overdue
        - If joined after April 1st of current year → first renewal is March 31st next year
          → no renewal status yet (unknown)
        - 'renewed'  : has a verified payment for the current membership year
        - 'overdue'  : due date has passed, no verified payment
        - 'due_soon' : due within 14 days, no verified payment
        - 'unknown'  : joined this membership year, first renewal not yet due
        """
        from django.utils import timezone
        from applications.signals import get_annual_renewal_date

        today = timezone.now().date()
        current_year_april_1 = today.replace(month=4, day=1, year=today.year if today.month >= 4 else today.year)

        # Use stored due date or derive from created_at
        due_date = obj.subscription_due_date
        if not due_date and obj.created_at:
            join_date = obj.created_at.date() if hasattr(obj.created_at, 'date') else obj.created_at
            due_date = get_annual_renewal_date(join_date)
            try:
                obj.__class__.objects.filter(pk=obj.pk).update(subscription_due_date=due_date)
            except Exception:
                pass

        if not due_date:
            return 'unknown'

        # If joined after April 1st of the current membership year,
        # their first renewal hasn't come yet
        join_date = obj.created_at.date() if hasattr(obj.created_at, 'date') else obj.created_at
        membership_year_start = today.replace(month=4, day=1) if today.month >= 4 else today.replace(month=4, day=1, year=today.year - 1)
        if join_date >= membership_year_start and due_date > today:
            return 'unknown'

        # Check for verified payment in the current membership year
        try:
            from payments.models import ManualPayment
            # Current membership year runs April 1 to March 31
            year_start = membership_year_start
            year_end = year_start.replace(year=year_start.year + 1, month=3, day=31)
            has_paid = ManualPayment.objects.filter(
                user=obj,
                payment_type='membership_renewal',
                status='verified',
                created_at__date__gte=year_start,
                created_at__date__lte=year_end,
            ).exists()
            if has_paid:
                return 'renewed'
        except Exception:
            pass

        days_remaining = (due_date - today).days
        if days_remaining < 0:
            return 'overdue'
        elif days_remaining <= 14:
            return 'due_soon'
        # Due date is in the future but no payment yet — still overdue from last year
        return 'overdue'

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
    
    def get_has_documents(self, obj):
        """Check if user has any documents (member documents or proof of payments)"""
        from payments.models import RenewalProofOfPayment
        
        member_docs_count = obj.member_documents.count()
        proof_of_payments_count = obj.renewal_proofs.count()
        
        return (member_docs_count + proof_of_payments_count) > 0
    
    def get_document_count(self, obj):
        """Count total documents including member documents and proof of payments"""
        from payments.models import RenewalProofOfPayment
        
        member_docs_count = obj.member_documents.count()
        proof_of_payments_count = obj.renewal_proofs.count()
        
        return member_docs_count + proof_of_payments_count
    
    def get_last_document_upload(self, obj):
        """Get the most recent document upload date from either member documents or proof of payments"""
        from payments.models import RenewalProofOfPayment
        from django.db.models import Max
        
        # Get latest member document upload
        latest_member_doc = obj.member_documents.aggregate(Max('uploaded_at'))['uploaded_at__max']
        
        # Get latest proof of payment upload
        latest_proof = obj.renewal_proofs.aggregate(Max('created_at'))['created_at__max']
        
        # Return the most recent of the two
        if latest_member_doc and latest_proof:
            return max(latest_member_doc, latest_proof)
        elif latest_member_doc:
            return latest_member_doc
        elif latest_proof:
            return latest_proof
        else:
            return None


class SuspendMemberSerializer(serializers.Serializer):
    """
    Serializer for suspending a member
    """
    reason = serializers.CharField(
        max_length=500,
        help_text="Reason for suspending the member"
    )
    suspension_type = serializers.ChoiceField(
        choices=['non_payment', 'policy_violation'],
        default='non_payment',
        help_text="Type of suspension: non_payment or policy_violation"
    )


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


# Bulk Registration Serializers

class BulkMemberEntrySerializer(serializers.Serializer):
    """Serializer for a single member entry in bulk registration"""
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=True, allow_blank=False)
    icpau_registration_number = serializers.CharField(max_length=50, required=True, allow_blank=False)


class BulkMemberRegistrationSerializer(serializers.Serializer):
    """Serializer for bulk member registration"""
    members = BulkMemberEntrySerializer(many=True)

    def validate_members(self, value):
        if not value:
            raise serializers.ValidationError("At least one member is required.")
        # Check for duplicate emails within the submitted list
        emails = [m['email'].lower() for m in value]
        if len(emails) != len(set(emails)):
            raise serializers.ValidationError("Duplicate emails found in the submitted list.")
        # Normalize emails in place
        for m in value:
            m['email'] = m['email'].lower()
        return value
