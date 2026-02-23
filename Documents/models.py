from django.db import models
from django.conf import settings
from applications.models import Application
import os
from datetime import datetime


def get_application_document_path(instance, filename):
    """
    Generate organized file path for application documents.
    Format: application_documents/{application_id}/{timestamp}_{filename}
    """
    # Get the application ID
    app_id = instance.application.id if instance.application else 'unassigned'
    
    # Get timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Clean filename - remove spaces and special characters
    clean_filename = filename.replace(' ', '_').replace('(', '').replace(')', '')
    
    # Construct path: application_documents/app_123/20260219_143022_document.pdf
    return os.path.join('application_documents', f'app_{app_id}', f'{timestamp}_{clean_filename}')


def get_member_document_path(instance, filename):
    """
    Generate organized file path for member documents.
    Format: member_documents/{user_id}/{timestamp}_{filename}
    """
    # Get the user ID
    user_id = instance.user.id if instance.user else 'unassigned'
    
    # Get timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Clean filename
    clean_filename = filename.replace(' ', '_').replace('(', '').replace(')', '')
    
    # Construct path: member_documents/user_123/20260219_143022_document.pdf
    return os.path.join('member_documents', f'user_{user_id}', f'{timestamp}_{clean_filename}')


class Document(models.Model):
    """
    Represents a document uploaded as part of a membership application.
    Stored in the Documents app, but linked to Application records.
    """
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to=get_application_document_path)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    file_type = models.CharField(max_length=50)
    document_type = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=[
            ('approved', 'Approved'),
            ('pending', 'Pending'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
        ],
        default='pending'
    )
    expiry_date = models.DateField(null=True, blank=True)
    admin_feedback = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Application Document'
        verbose_name_plural = 'Application Documents'
        db_table = 'applications_document'
        managed = False

    def __str__(self):
        owner = None
        if self.application and self.application.username:
            owner = self.application.username
        return f"{self.file_name} - {owner or 'unknown'}"


class MemberDocument(models.Model):
    """
    Represents a document uploaded by a member after approval.
    Stored separately from application documents.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='member_documents',
    )
    file = models.FileField(upload_to=get_member_document_path)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    file_type = models.CharField(max_length=50)
    document_type = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=[
            ('approved', 'Approved'),
            ('pending', 'Pending'),
        ],
        default='pending'
    )
    expiry_date = models.DateField(null=True, blank=True)
    admin_feedback = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Member Document'
        verbose_name_plural = 'Member Documents'

    def __str__(self):
        return f"{self.file_name} - {self.user.email}"
