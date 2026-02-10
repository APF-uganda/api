from django.db import models
from django.db.models import Q
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
      
    AGE_RANGE_CHOICES = [
       ('18 – 24', '18 – 24'),
       ('25 – 34', '25 – 34'),
       ('35 – 44', '35 – 44'),
       ('45 – 54', '45 – 54'),
       ('55 – 64', '55 – 64'),
       ('65+', '65+'),
    ]


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
    
    def __str__(self):
        return f"{self.username} - {self.email} ({self.status})"


