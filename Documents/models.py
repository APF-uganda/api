from django.db import models
from django.conf import settings
from applications.models import Application


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
    file = models.FileField(upload_to='application_documents/')
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
    file = models.FileField(upload_to='application_documents/')
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
