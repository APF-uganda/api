from django.db import models
from django.contrib.auth import get_user_model
from authentication.models import User
from Documents.models import MemberDocument
from django.utils import timezone

# Use get_user_model for consistency
AuthUser = get_user_model()


class MembershipStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    PENDING = 'PENDING', 'Pending'


class DocumentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class SuspendedMember(models.Model):
    """
    Tracks suspended members with reasons and timestamps
    """
    user = models.OneToOneField(
        AuthUser,
        on_delete=models.CASCADE,
        related_name='suspension_record'
    )
    suspension_reason = models.TextField(
        help_text="Reason for suspending the member"
    )
    suspended_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the member was suspended"
    )
    reactivated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the member was reactivated (if applicable)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_management_suspended_members'
        verbose_name = 'Suspended Member'
        verbose_name_plural = 'Suspended Members'

    def __str__(self):
        return f"Suspension record for {self.user.email}"


class ProcessedDocument(models.Model):
    """
    Tracks documents that have been processed (approved/rejected)
    """
    document = models.OneToOneField(
        MemberDocument,
        on_delete=models.CASCADE,
        related_name='processed_record'
    )
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the document was approved (if applicable)"
    )
    approved_by = models.ForeignKey(
        AuthUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_documents',
        help_text="Admin who approved the document"
    )
    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the document was rejected (if applicable)"
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejecting the document"
    )
    processed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the document was processed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_management_processed_documents'
        verbose_name = 'Processed Document'
        verbose_name_plural = 'Processed Documents'

    def __str__(self):
        return f"{self.document.file_name} - {self.status}"



# Membership Invoice Models for Automated Renewal System

from decimal import Decimal


class MembershipInvoice(models.Model):
    """
    Membership renewal invoice model
    Tracks invoices generated for annual membership renewals
    """
    
    STATUS_PENDING = 'pending'
    STATUS_PARTIAL = 'partial'
    STATUS_PAID = 'paid'
    STATUS_OVERDUE = 'overdue'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Payment'),
        (STATUS_PARTIAL, 'Partially Paid'),
        (STATUS_PAID, 'Fully Paid'),
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Invoice identification
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Member details
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='membership_invoices')
    
    # Invoice details
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    
    # Membership period
    period_start = models.DateField(help_text="Membership period start date (April 1st)")
    period_end = models.DateField(help_text="Membership period end date (March 31st)")
    
    # Financial details
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('150000.00'))
    previous_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance_due = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    
    # Email tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['invoice_date', 'status']),
            models.Index(fields=['period_start', 'period_end']),
        ]
        verbose_name = 'Membership Invoice'
        verbose_name_plural = 'Membership Invoices'
    
    def __str__(self):
        return f"{self.invoice_number} - {self.user.email} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Calculate balance due
        self.balance_due = self.total_amount - self.amount_paid
        
        # Update status based on payment
        if self.amount_paid >= self.total_amount:
            self.status = self.STATUS_PAID
            if not self.paid_at:
                self.paid_at = timezone.now()
        elif self.amount_paid > 0:
            self.status = self.STATUS_PARTIAL
        elif self.due_date < timezone.now().date() and self.amount_paid == 0:
            self.status = self.STATUS_OVERDUE
        
        super().save(*args, **kwargs)
    
    def record_payment(self, amount):
        """
        Record a payment against this invoice
        
        Args:
            amount: Decimal amount paid
        """
        self.amount_paid += Decimal(str(amount))
        self.save()
    
    def is_overdue(self):
        """Check if invoice is overdue"""
        return self.due_date < timezone.now().date() and self.balance_due > 0
    
    def get_payment_percentage(self):
        """Get percentage of invoice paid"""
        if self.total_amount == 0:
            return 0
        return (self.amount_paid / self.total_amount) * 100


class InvoicePaymentLink(models.Model):
    """
    Links payments to invoices for proper ledger accounting
    """
    invoice = models.ForeignKey(MembershipInvoice, on_delete=models.CASCADE, related_name='payment_links')
    payment = models.ForeignKey('payments.Payment', on_delete=models.CASCADE, related_name='invoice_links')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice Payment Link'
        verbose_name_plural = 'Invoice Payment Links'
    
    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.payment.transaction_reference} - UGX {self.amount}"


class AdminNote(models.Model):
    """
    Admin notes on member records for tracking interactions and important information
    """
    member = models.ForeignKey(
        AuthUser,
        on_delete=models.CASCADE,
        related_name='admin_notes',
        help_text="Member this note is about"
    )
    admin = models.ForeignKey(
        AuthUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_notes',
        help_text="Admin who created this note"
    )
    note_text = models.TextField(
        help_text="Content of the note"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_management_admin_notes'
        ordering = ['-created_at']
        verbose_name = 'Admin Note'
        verbose_name_plural = 'Admin Notes'
    
    def __str__(self):
        return f"Note by {self.admin.email if self.admin else 'Unknown'} on {self.member.email} - {self.created_at.strftime('%Y-%m-%d')}"
