"""
Serializers for payment API endpoints.
"""
from rest_framework import serializers
from decimal import Decimal
from .models import Payment


class ManualPaymentSerializer(serializers.ModelSerializer):
    """Serializer for manual payment model."""
    user_name = serializers.SerializerMethodField()
    application_id = serializers.CharField(source='application.application_id', read_only=True)
    verified_by_name = serializers.SerializerMethodField()
    
    class Meta:
        from .models import ManualPayment
        model = ManualPayment
        fields = [
            'id',
            'user_name',
            'application_id',
            'invoice_number',
            'application_reference',
            'reference',
            'description',
            'amount',
            'currency',
            'proof_of_payment',
            'status',
            'verification_notes',
            'verified_by_name',
            'verified_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user_name',
            'application_id',
            'verified_by_name',
            'verified_at',
            'created_at',
            'updated_at',
        ]
    
    def get_user_name(self, obj):
        """Get user's full name."""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return "Unknown"
    
    def get_verified_by_name(self, obj):
        """Get name of admin who verified the payment."""
        if obj.verified_by:
            return f"{obj.verified_by.first_name} {obj.verified_by.last_name}".strip() or obj.verified_by.email
        return None


class PaymentInitiationResponseSerializer(serializers.Serializer):
    """Serializer for payment initiation response."""
    success = serializers.BooleanField()
    payment_id = serializers.UUIDField()
    transaction_reference = serializers.CharField()
    message = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()


class PaymentStatusResponseSerializer(serializers.Serializer):
    """Serializer for payment status response."""
    status = serializers.CharField()
    message = serializers.CharField()
    provider_transaction_id = serializers.CharField(allow_null=True)
    updated_at = serializers.DateTimeField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    provider = serializers.CharField()


class PaymentRetryResponseSerializer(serializers.Serializer):
    """Serializer for payment retry response."""
    success = serializers.BooleanField()
    new_payment_id = serializers.UUIDField(allow_null=True)
    transaction_reference = serializers.CharField(allow_null=True)
    message = serializers.CharField()


class PaymentCancellationResponseSerializer(serializers.Serializer):
    """Serializer for payment cancellation response."""
    success = serializers.BooleanField()
    message = serializers.CharField()


class MembershipFeeResponseSerializer(serializers.Serializer):
    """Serializer for membership fee response."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for payment history list endpoint."""
    masked_phone = serializers.SerializerMethodField()
    invoice_details = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_reference',
            'provider_transaction_id',
            'invoice_number',
            'amount',
            'currency',
            'provider',
            'status',
            'error_message',
            'created_at',
            'updated_at',
            'completed_at',
            'masked_phone',
            'invoice_details',
        ]
        read_only_fields = fields

    def get_masked_phone(self, obj):
        return obj.get_masked_phone()
    
    def get_invoice_details(self, obj):
        """Get invoice details if payment is linked to an invoice."""
        if not obj.invoice_number:
            return None
        
        try:
            from admin_management.models import MembershipInvoice
            invoice = MembershipInvoice.objects.filter(invoice_number=obj.invoice_number).first()
            if invoice:
                return {
                    'invoice_number': invoice.invoice_number,
                    'total_amount': str(invoice.total_amount),
                    'amount_paid': str(invoice.amount_paid),
                    'balance_due': str(invoice.balance_due),
                    'status': invoice.status,
                    'due_date': invoice.due_date.isoformat(),
                }
        except Exception:
            pass
        
        return None


class AdminTransactionSerializer(serializers.ModelSerializer):
    """Serializer for admin transaction history view."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    application_id = serializers.IntegerField(source='application.id', read_only=True)
    masked_phone = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    invoice_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_reference',
            'provider_transaction_id',
            'invoice_number',
            'user_email',
            'user_name',
            'application_id',
            'masked_phone',
            'amount',
            'currency',
            'provider',
            'provider_display',
            'status',
            'status_display',
            'error_message',
            'created_at',
            'updated_at',
            'completed_at',
            'ip_address',
            'invoice_details',
        ]
    
    def get_user_name(self, obj):
        """Get user's full name."""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return "N/A"
    
    def get_masked_phone(self, obj):
        """Get masked phone number."""
        return obj.get_masked_phone()
    
    def get_invoice_details(self, obj):
        """Get invoice details if payment is linked to an invoice."""
        if not obj.invoice_number:
            return None
        
        try:
            from admin_management.models import MembershipInvoice
            invoice = MembershipInvoice.objects.filter(invoice_number=obj.invoice_number).first()
            if invoice:
                return {
                    'invoice_number': invoice.invoice_number,
                    'total_amount': str(invoice.total_amount),
                    'amount_paid': str(invoice.amount_paid),
                    'balance_due': str(invoice.balance_due),
                    'status': invoice.status,
                    'due_date': invoice.due_date.isoformat(),
                }
        except Exception:
            pass
        
        return None


class TransactionRevenueSerializer(serializers.Serializer):
    """Serializer for revenue statistics."""
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions = serializers.IntegerField()
    completed_transactions = serializers.IntegerField()
    pending_transactions = serializers.IntegerField()
    failed_transactions = serializers.IntegerField()
    mtn_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    airtel_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()


class PaymentInitiationSerializer(serializers.Serializer):
    """Serializer for payment initiation request."""
    phone_number = serializers.CharField(
        max_length=12,
        min_length=12,
        help_text="Phone number in format 256XXXXXXXXX"
    )
    provider = serializers.ChoiceField(
        choices=['mtn', 'airtel', 'pesapal'],
        help_text="Payment provider (mtn, airtel, or pesapal)"
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Payment amount (optional, defaults to membership fee)"
    )
    application_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional application ID to link payment"
    )
    invoice_number = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=50,
        help_text="Optional membership renewal invoice number"
    )
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if not value.startswith('256'):
            raise serializers.ValidationError("Phone number must start with 256")
        if not value[3:].isdigit():
            raise serializers.ValidationError("Phone number must contain only digits after 256")
        return value


class PaymentInitiationResponseSerializer(serializers.Serializer):
    """Serializer for payment initiation response."""
    success = serializers.BooleanField()
    payment_id = serializers.UUIDField()
    transaction_reference = serializers.CharField()
    message = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()


class PaymentStatusResponseSerializer(serializers.Serializer):
    """Serializer for payment status response."""
    status = serializers.CharField()
    message = serializers.CharField()
    provider_transaction_id = serializers.CharField(allow_null=True)
    updated_at = serializers.DateTimeField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    provider = serializers.CharField()


class PaymentRetryResponseSerializer(serializers.Serializer):
    """Serializer for payment retry response."""
    success = serializers.BooleanField()
    new_payment_id = serializers.UUIDField(allow_null=True)
    transaction_reference = serializers.CharField(allow_null=True)
    message = serializers.CharField()


class PaymentCancellationResponseSerializer(serializers.Serializer):
    """Serializer for payment cancellation response."""
    success = serializers.BooleanField()
    message = serializers.CharField()


class MembershipFeeResponseSerializer(serializers.Serializer):
    """Serializer for membership fee response."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for payment history list endpoint."""
    masked_phone = serializers.SerializerMethodField()
    invoice_details = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_reference',
            'provider_transaction_id',
            'invoice_number',
            'amount',
            'currency',
            'provider',
            'status',
            'error_message',
            'created_at',
            'updated_at',
            'completed_at',
            'masked_phone',
            'invoice_details',
        ]
        read_only_fields = fields

    def get_masked_phone(self, obj):
        return obj.get_masked_phone()
    
    def get_invoice_details(self, obj):
        """Get invoice details if payment is linked to an invoice."""
        if not obj.invoice_number:
            return None
        
        try:
            from admin_management.models import MembershipInvoice
            invoice = MembershipInvoice.objects.filter(invoice_number=obj.invoice_number).first()
            if invoice:
                return {
                    'invoice_number': invoice.invoice_number,
                    'total_amount': str(invoice.total_amount),
                    'amount_paid': str(invoice.amount_paid),
                    'balance_due': str(invoice.balance_due),
                    'status': invoice.status,
                    'due_date': invoice.due_date.isoformat(),
                }
        except Exception:
            pass
        
        return None


class AdminTransactionSerializer(serializers.ModelSerializer):
    """Serializer for admin transaction history view."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    application_id = serializers.IntegerField(source='application.id', read_only=True)
    masked_phone = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    invoice_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_reference',
            'provider_transaction_id',
            'invoice_number',
            'user_email',
            'user_name',
            'application_id',
            'masked_phone',
            'amount',
            'currency',
            'provider',
            'provider_display',
            'status',
            'status_display',
            'error_message',
            'created_at',
            'updated_at',
            'completed_at',
            'ip_address',
            'invoice_details',
        ]
    
    def get_user_name(self, obj):
        """Get user's full name."""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return "N/A"
    
    def get_masked_phone(self, obj):
        """Get masked phone number."""
        return obj.get_masked_phone()
    
    def get_invoice_details(self, obj):
        """Get invoice details if payment is linked to an invoice."""
        if not obj.invoice_number:
            return None
        
        try:
            from admin_management.models import MembershipInvoice
            invoice = MembershipInvoice.objects.filter(invoice_number=obj.invoice_number).first()
            if invoice:
                return {
                    'invoice_number': invoice.invoice_number,
                    'total_amount': str(invoice.total_amount),
                    'amount_paid': str(invoice.amount_paid),
                    'balance_due': str(invoice.balance_due),
                    'status': invoice.status,
                    'due_date': invoice.due_date.isoformat(),
                }
        except Exception:
            pass
        
        return None


class TransactionRevenueSerializer(serializers.Serializer):
    """Serializer for revenue statistics."""
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions = serializers.IntegerField()
    completed_transactions = serializers.IntegerField()
    pending_transactions = serializers.IntegerField()
    failed_transactions = serializers.IntegerField()
    mtn_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    airtel_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
