"""
Payment models for mobile money integration.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings

User = get_user_model()


class Payment(models.Model):
    """
    Payment transaction model for mobile money payments.
    Stores all payment transaction data with audit trail.
    """
    
    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_TIMEOUT = 'timeout'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_TIMEOUT, 'Timeout'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Provider choices
    PROVIDER_MTN = 'mtn'
    PROVIDER_AIRTEL = 'airtel'
    
    PROVIDER_CHOICES = [
        (PROVIDER_MTN, 'MTN Mobile Money'),
        (PROVIDER_AIRTEL, 'Airtel Money'),
    ]
    
    # Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_reference = models.CharField(max_length=100, unique=True, db_index=True)
    provider_transaction_id = models.CharField(max_length=200, null=True, blank=True)
    
    # User and application linkage
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    # Payment details
    phone_number = models.CharField(max_length=255)  # Encrypted
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='UGX')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    
    # Metadata
    error_message = models.TextField(null=True, blank=True)
    provider_response = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['provider', 'status']),
        ]
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
    
    def __str__(self):
        return f"{self.provider.upper()} - {self.transaction_reference} - {self.status}"
    
    def mark_completed(self, provider_tx_id, response_data=None):
        """Update payment status to completed."""
        self.status = self.STATUS_COMPLETED
        self.provider_transaction_id = provider_tx_id
        self.completed_at = timezone.now()
        if response_data:
            self.provider_response = response_data
        self.save()
    
    def mark_failed(self, error_message, response_data=None):
        """Update payment status to failed."""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        if response_data:
            self.provider_response = response_data
        self.save()
    
    def mark_timeout(self):
        """Update payment status to timeout."""
        self.status = self.STATUS_TIMEOUT
        self.error_message = "Payment verification timed out after 90 seconds"
        self.save()
    
    def can_retry(self):
        """Check if payment can be retried."""
        return self.status in [self.STATUS_FAILED, self.STATUS_TIMEOUT]
    
    def get_masked_phone(self):
        """Return phone number with only last 4 digits visible."""
        try:
            # Decrypt phone number first
            decrypted = self._decrypt_phone()
            if len(decrypted) < 8:
                return '****'
            return f"{decrypted[:3]}****{decrypted[-4:]}"
        except Exception:
            return '****'
    
    def _decrypt_phone(self):
        """Decrypt phone number for internal use."""
        try:
            encryption_key = getattr(settings, 'PHONE_ENCRYPTION_KEY', None)
            if not encryption_key:
                return self.phone_number
            
            cipher = Fernet(encryption_key.encode())
            return cipher.decrypt(self.phone_number.encode()).decode()
        except Exception:
            return self.phone_number


class PaymentConfig(models.Model):
    """
    Payment configuration model for storing configurable payment settings.
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment Configuration'
        verbose_name_plural = 'Payment Configurations'
    
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    @classmethod
    def get_membership_fee(cls):
        """Get current membership fee amount."""
        try:
            config = cls.objects.get(key='membership_fee_ugx')
            return Decimal(config.value)
        except cls.DoesNotExist:
            return Decimal('50000.00')  # Default fallback
        except (ValueError, TypeError):
            return Decimal('50000.00')  # Default fallback
