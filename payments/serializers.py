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
