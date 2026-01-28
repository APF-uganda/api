from django.db import models
from django.conf import settings


class Application(models.Model):
    """
    Represents a membership application submitted by a user.
    Stores account details, personal information, payment information, and status.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    # Account Details
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    
    # Payment Information
    payment_method = models.CharField(max_length=20)
    # Mobile money fields
    payment_phone = models.CharField(max_length=20, blank=True)
    # Credit card fields
    payment_card_number = models.CharField(max_length=50, blank=True)  # Last 4 digits only for security
    payment_card_expiry = models.CharField(max_length=10, blank=True)
    payment_card_cvv = models.CharField(max_length=10, blank=True)  # Should not be stored in production
    payment_cardholder_name = models.CharField(max_length=100, blank=True)
    # Payment processing fields
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('idle', 'Idle'),
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed')
        ],
        default='idle'
    )
    payment_transaction_reference = models.CharField(max_length=100, blank=True)
    payment_error_message = models.TextField(blank=True)
    
    # Metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to User model (nullable for backward compatibility)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications'
    )
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Membership Application'
        verbose_name_plural = 'Membership Applications'
    
    def __str__(self):
        return f"{self.username} - {self.email} ({self.status})"


class Document(models.Model):
    """
    Represents a document uploaded as part of a membership application.
    Associated with an Application via foreign key.
    """
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file = models.FileField(upload_to='application_documents/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Application Document'
        verbose_name_plural = 'Application Documents'
    
    def __str__(self):
        return f"{self.file_name} - {self.application.username}"
