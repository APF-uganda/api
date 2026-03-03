"""
Serializers for payment API endpoints.
"""
from rest_framework import serializers
from decimal import Decimal
from .models import Payment


class PaymentInitiationSerializer(serializers.Serializer):
    """Serializer for payment initiation request."""
    phone_number = serializers.CharField(
        max_length=12,
        min_length=12,
        help_text="Phone number in format 256XXXXXXXXX"
    )
    provider = serializers.ChoiceField(
        choices=['mtn', 'airtel'],
        help_text="Payment provider (mtn or airtel)"
    )
    application_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional application ID to link payment"
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

    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_reference',
            'provider_transaction_id',
            'amount',
            'currency',
            'provider',
            'status',
            'error_message',
            'created_at',
            'updated_at',
            'completed_at',
            'masked_phone',
        ]
        read_only_fields = fields

    def get_masked_phone(self, obj):
        return obj.get_masked_phone()


class AdminTransactionSerializer(serializers.ModelSerializer):
    """Serializer for admin transaction history view."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    application_id = serializers.IntegerField(source='application.id', read_only=True)
    masked_phone = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_reference',
            'provider_transaction_id',
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
        ]
    
    def get_user_name(self, obj):
        """Get user's full name."""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return "N/A"
    
    def get_masked_phone(self, obj):
        """Get masked phone number."""
        return obj.get_masked_phone()


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
