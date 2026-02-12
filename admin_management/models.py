from django.db import models
from django.conf import settings
from authentication.models import User
from Documents.models import MemberDocument
from django.utils import timezone


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
        settings.AUTH_USER_MODEL,
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
        settings.AUTH_USER_MODEL,
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