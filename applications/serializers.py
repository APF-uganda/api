import re
from datetime import date, timedelta
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Application
from Documents.models import Document

MTN_PREFIXES = (
    '25677', '25678', '25676', '25679' # MTN Uganda
)

AIRTEL_PREFIXES = (
    '25670', '25675', '25674'  # Airtel Uganda
)

class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for Document model.
    Handles nested document data for application submissions.
    """
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = ['id', 'file', 'file_url', 'file_name', 'file_size', 'file_type', 'document_type', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'file_url']
    
    def get_file_url(self, obj):
        """Return the full URL for the file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            # Fallback to relative URL if no request context
            return obj.file.url
        return None


class ApplicationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing applications to improve performance
    """
    name = serializers.SerializerMethodField()
    icpaCertNo = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'name',
            'icpau_certificate_number', 'icpaCertNo', 'status', 'payment_status', 'submitted_at', 'updated_at'
        ]
        read_only_fields = ['id', 'submitted_at', 'updated_at', 'name', 'icpaCertNo']
    
    def get_name(self, obj):
        """Return concatenated full name from first_name and last_name"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        elif obj.first_name:
            return obj.first_name
        elif obj.last_name:
            return obj.last_name
        else:
            return ""
    
    def get_icpaCertNo(self, obj):
        """Return ICPAU certificate number as icpaCertNo for frontend compatibility"""
        return obj.icpau_certificate_number or ""


class ApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for Application model.
    Includes comprehensive field validation for all application data.
    """
    documents = DocumentSerializer(many=True, read_only=True)
    name = serializers.SerializerMethodField()
    icpaCertNo = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'username', 'email', 'password_hash', 'first_name', 'last_name', 'name',
            'age_range', 'phone_number', 'address', 'national_id_number', 'icpau_certificate_number',
            'icpaCertNo',
            'payment_method', 'payment_phone',
            'payment_card_number', 'payment_card_expiry', 'payment_card_cvv',
            'payment_cardholder_name',
            'payment_status', 'payment_transaction_reference', 'payment_error_message',
            'payment_amount', 'status', 'submitted_at', 'updated_at', 'documents'
        ]
        read_only_fields = ['id', 'status', 'submitted_at', 'updated_at', 'name', 'icpaCertNo']
        extra_kwargs = {
            'password_hash': {'write_only': True},
            'payment_card_cvv': {'write_only': True}  # Never return CVV
        }
    
    def validate_email(self, value):
        """
        Validate email format.
        Requirements: 2.2, 10.4
        """
        if not value:
            raise serializers.ValidationError("Email is required.")
        
        # Email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise serializers.ValidationError("Enter a valid email address.")
        
        # Enforce uniqueness only for non-rejected applications
        if Application.objects.filter(email__iexact=value).exclude(status='rejected').exists():
            raise serializers.ValidationError("Membership Application with this email already exists.")

        return value
    
    def validate_phone_number(self, value):
        """
        Validate phone number format (256XXXXXXXXX).
        Requirements: 3.2, 10.4
        """
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        
        # Phone number pattern: 256 followed by 9 digits
        phone_pattern = r'^256\d{9}$'
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("Phone number must be in format 256XXXXXXXXX.")
        
        return value
    
    def validate_national_id_number(self, value):
        """
        Validate national ID number format.
        Must start with CF or CM and be exactly 13 characters total (alphanumeric).
        Requirements: 10.4
        """
        if not value:
            raise serializers.ValidationError("National ID number is required.")
        
        # National ID pattern: CF or CM followed by 11 alphanumeric characters (13 characters total)
        national_id_pattern = r'^(CF|CM)[A-Z0-9]{11}$'
        if not re.match(national_id_pattern, value.upper()):
            raise serializers.ValidationError(
                "National ID must start with CF or CM and be exactly 13 characters (letters and numbers, e.g., CF12345ABC67 or CM1234567890A)."
            )
        
        return value.upper()  # Normalize to uppercase

    def validate_username(self, value):
        if not value:
            raise serializers.ValidationError("Username is required.")

        if Application.objects.filter(username__iexact=value).exclude(status='rejected').exists():
            raise serializers.ValidationError("Membership Application with this username already exists.")

        return value
    
    def validate(self, data):
        """
        Cross-field validation for payment data based on payment method.
        Requirements: 10.4
        """
        payment_method = data.get('payment_method')
        
        if not payment_method:
            raise serializers.ValidationError({
                'payment_method': 'Payment method is required.'
            })
        
        # Validate MTN Mobile Money payment
        if payment_method == 'mtn':
            self._validate_mtn_payment(data)
        
        # Validate Airtel Money payment
        elif payment_method == 'airtel':
            self._validate_airtel_payment(data)
        
        # Validate Credit Card payment
        elif payment_method == 'credit_card':
            self._validate_credit_card_payment(data)
        
        else:
            raise serializers.ValidationError({
                'payment_method': 'Invalid payment method. Must be mtn, airtel, or credit_card.'
            })
        
        return data
    
    def _validate_mtn_payment(self, data):
        """
        Validate MTN Mobile Money payment data.
        Requirements: 6.2, 10.4
        """
        errors = {}
        
        payment_phone = data.get('payment_phone')
        
        # Validate phone number
        if not payment_phone:
            errors['payment_phone'] = 'Phone number is required for MTN payment.'
        else:
            phone_pattern = r'^256\d{9}$'
            if not re.match(phone_pattern, payment_phone):
                errors['payment_phone'] = 'Phone number must be in format 256XXXXXXXXX.'

            elif not payment_phone.startswith(MTN_PREFIXES):
                errors['payment_phone'] = 'Please enter a valid MTN number.'
        
        if errors:
            raise serializers.ValidationError(errors)
    
    def _validate_airtel_payment(self, data):
        """
        Validate Airtel Money payment data.
        Requirements: 7.2, 10.4
        """
        errors = {}
        
        payment_phone = data.get('payment_phone')
        
        # Validate phone number
        if not payment_phone:
            errors['payment_phone'] = 'Phone number is required for Airtel payment.'
        else:
            phone_pattern = r'^256\d{9}$'
            if not re.match(phone_pattern, payment_phone):
                errors['payment_phone'] = 'Phone number must be in format 256XXXXXXXXX.'

            elif not payment_phone.startswith(AIRTEL_PREFIXES):
               errors['payment_phone'] = 'Please enter a valid Airtel number.'
        
        if errors:
            raise serializers.ValidationError(errors)
    
    def _validate_credit_card_payment(self, data):
        """
        Validate Credit Card payment data.
        Requirements: 8.2, 8.3, 8.4, 10.4
        """
        errors = {}
        
        payment_card_number = data.get('payment_card_number')
        payment_card_expiry = data.get('payment_card_expiry')
        payment_card_cvv = data.get('payment_card_cvv')
        payment_cardholder_name = data.get('payment_cardholder_name')
        
        # Validate card number (accepts both formatted with spaces and unformatted)
        if not payment_card_number:
            errors['payment_card_number'] = 'Card number is required for Credit Card payment.'
        else:
            # Remove spaces and dashes for validation
            card_digits = payment_card_number.replace(' ', '').replace('-', '')
            if not re.match(r'^\d{13,19}$', card_digits):
                errors['payment_card_number'] = 'Card number must be 13-19 digits.'
        
        # Validate expiry date
        if not payment_card_expiry:
            errors['payment_card_expiry'] = 'Expiry date is required for Credit Card payment.'
        else:
            expiry_pattern = r'^(0[1-9]|1[0-2])/\d{2}$'
            if not re.match(expiry_pattern, payment_card_expiry):
                errors['payment_card_expiry'] = 'Expiry date must be in format MM/YY.'
            else:
                # Check if expiry date is not in the past
                try:
                    month, year = payment_card_expiry.split('/')
                    expiry_month = int(month)
                    expiry_year = int('20' + year)
                    
                    today = date.today()
                    # Card expires at the end of the expiry month
                    if expiry_year < today.year or (expiry_year == today.year and expiry_month < today.month):
                        errors['payment_card_expiry'] = 'Card has expired.'
                except (ValueError, IndexError):
                    errors['payment_card_expiry'] = 'Invalid expiry date format.'
        
        # Validate CVV (accepts 3-4 digits for different card types)
        if not payment_card_cvv:
            errors['payment_card_cvv'] = 'CVV is required for Credit Card payment.'
        else:
            cvv_pattern = r'^\d{3,4}$'
            if not re.match(cvv_pattern, payment_card_cvv):
                errors['payment_card_cvv'] = 'CVV must be 3-4 digits.'
        
        # Validate cardholder name
        if not payment_cardholder_name or not payment_cardholder_name.strip():
            errors['payment_cardholder_name'] = 'Cardholder name is required for Credit Card payment.'
        
        if errors:
            raise serializers.ValidationError(errors)
    
    def create(self, validated_data):
        """
        Override create method to hash password before saving
        
        Requirements: 12.6
        """
        # Hash the password before saving
        if 'password_hash' in validated_data:
            validated_data['password_hash'] = make_password(validated_data['password_hash'])
        
        # Create and return the application instance
        return super().create(validated_data)
    
    def get_name(self, obj):
        """Return concatenated full name from first_name and last_name"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        elif obj.first_name:
            return obj.first_name
        elif obj.last_name:
            return obj.last_name
        else:
            return ""
    
    def get_icpaCertNo(self, obj):
        """Return ICPAU certificate number as icpaCertNo for frontend compatibility"""
        return obj.icpau_certificate_number or ""
