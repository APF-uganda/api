from django.db import models
from django.db.models import Q
from django.conf import settings
from datetime import datetime


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
      
    AGE_RANGE_CHOICES = [
       ('18 – 24', '18 – 24'),
       ('25 – 34', '25 – 34'),
       ('35 – 44', '35 – 44'),
       ('45 – 54', '45 – 54'),
       ('55 – 64', '55 – 64'),
       ('65+', '65+'),
    ]

    # Unique Application ID
    application_id = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique application identifier (e.g., APF-2026-000123)'
    )

    # Account Details
    username = models.CharField(max_length=150)
    email = models.EmailField()
    password_hash = models.CharField(max_length=255)
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age_range = models.CharField(
    max_length=10,
    choices=AGE_RANGE_CHOICES
    )
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    national_id_number = models.CharField(max_length=20, blank=True)
    icpau_certificate_number = models.CharField(max_length=50, blank=True)
    organization = models.CharField(max_length=200, blank=True, help_text='Organization/Firm name')
    
    # Document fields (for file uploads)
    icpau_cert_doc = models.FileField(
        upload_to='documents/icpau_certs/', 
        null=True, 
        blank=True,
        help_text='ICPAU Certificate document'
    )
    firm_license_doc = models.FileField(
        upload_to='documents/firm_licenses/', 
        null=True, 
        blank=True,
        help_text='Firm License document'
    )
    proof_of_payment_doc = models.FileField(
        upload_to='documents/payment_proofs/', 
        null=True, 
        blank=True,
        help_text='Proof of Payment document'
    )
    
    # Payment Information
    payment_method = models.CharField(max_length=20)
    payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=50000.00,
        help_text='Payment amount in UGX'
    )
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
            ('completed', 'Completed'),
            ('success', 'Success'),
            ('failed', 'Failed')
        ],
        default='idle'
    )
    payment_transaction_reference = models.CharField(max_length=100, blank=True)
    payment_error_message = models.TextField(blank=True)
    
    # Link to Payment model (for mobile money integration)
    current_payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_application',
        help_text='Current active payment for this application'
    )
    
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
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                condition=~Q(status='rejected'),
                name='uniq_application_email_not_rejected'
            ),
            models.UniqueConstraint(
                fields=['username'],
                condition=~Q(status='rejected'),
                name='uniq_application_username_not_rejected'
            ),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate application_id if not set"""
        if not self.application_id:
            self.application_id = self.generate_application_id()
        super().save(*args, **kwargs)
    
    def generate_application_id(self):
        """Generate a unique application ID in format APF-YYYY-NNNNNN"""
        current_year = datetime.now().year
        
        # Get the count of applications created this year
        year_count = Application.objects.filter(
            submitted_at__year=current_year
        ).count() + 1
        
        # Generate ID with zero-padded number
        application_id = f"APF-{current_year}-{year_count:06d}"
        
        # Ensure uniqueness (in case of race conditions)
        while Application.objects.filter(application_id=application_id).exists():
            year_count += 1
            application_id = f"APF-{current_year}-{year_count:06d}"
        
        return application_id
    
    def __str__(self):
        return f"{self.application_id} - {self.username} - {self.email} ({self.status})"


