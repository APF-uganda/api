"""
Webhook tracking models for payment status updates.
Tracks webhook notifications to enable webhook-first with polling fallback.
"""
import uuid
from django.db import models
from django.utils import timezone


class WebhookNotification(models.Model):
    """
    Tracks webhook notifications received from payment providers.
    Used to determine if polling fallback is needed.
    """
    
    # Status choices
    STATUS_RECEIVED = 'received'
    STATUS_PROCESSED = 'processed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_RECEIVED, 'Received'),
        (STATUS_PROCESSED, 'Processed'),
        (STATUS_FAILED, 'Failed'),
    ]
    
    # Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.CASCADE,
        related_name='webhook_notifications'
    )
    
    # Webhook details
    provider = models.CharField(max_length=20)
    transaction_reference = models.CharField(max_length=100, db_index=True)
    webhook_status = models.CharField(max_length=50)  # Provider's status value
    
    # Processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    error_message = models.TextField(null=True, blank=True)
    
    # Metadata
    payload = models.JSONField()
    signature = models.CharField(max_length=500)
    signature_valid = models.BooleanField(default=False)
    
    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['transaction_reference', 'received_at']),
            models.Index(fields=['payment', 'status']),
        ]
        verbose_name = 'Webhook Notification'
        verbose_name_plural = 'Webhook Notifications'
    
    def __str__(self):
        return f"{self.provider.upper()} - {self.transaction_reference} - {self.webhook_status}"
    
    def mark_processed(self):
        """Mark webhook as successfully processed."""
        self.status = self.STATUS_PROCESSED
        self.processed_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message: str):
        """Mark webhook processing as failed."""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.processed_at = timezone.now()
        self.save()


class PaymentStatusCheck(models.Model):
    """
    Tracks payment status check attempts (both webhook and polling).
    Provides audit trail and helps prevent duplicate checks.
    """
    
    # Check type choices
    TYPE_WEBHOOK = 'webhook'
    TYPE_POLLING = 'polling'
    TYPE_MANUAL = 'manual'
    
    TYPE_CHOICES = [
        (TYPE_WEBHOOK, 'Webhook'),
        (TYPE_POLLING, 'Polling'),
        (TYPE_MANUAL, 'Manual'),
    ]
    
    # Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.CASCADE,
        related_name='status_checks'
    )
    
    # Check details
    check_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status_before = models.CharField(max_length=20)
    status_after = models.CharField(max_length=20)
    
    # Result
    success = models.BooleanField(default=False)
    message = models.TextField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    
    # Timestamps
    checked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['payment', 'check_type', 'checked_at']),
        ]
        verbose_name = 'Payment Status Check'
        verbose_name_plural = 'Payment Status Checks'
    
    def __str__(self):
        return f"{self.payment.transaction_reference} - {self.check_type} - {self.checked_at}"
