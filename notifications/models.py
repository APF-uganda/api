from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from applications.models import Application

class Notification(models.Model):
    """
    Represents a notification sent to a user about their application status.
    """
    TYPE_CHOICES = [
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="info")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.user.username} - {self.type}"


class UserNotification(models.Model):
    """
    General in-app notifications for users (not tied to applications)
    Used for announcements, system messages, etc.
    """
    TYPE_CHOICES = [
        ("announcement", "Announcement"),
        ("system", "System"),
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]
    
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="info")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class Announcement(models.Model):
    """
    Admin announcements sent to groups of users via email and/or in-app notifications.
    Consolidated from the former AdminNotifications app.
    """
    AUDIENCE_CHOICES = [
        ('all_users', 'All Users'),
        ('members', 'Members'),
        ('applicants', 'Applicants'),
        ('admins', 'Admins'),
        ('expired_members', 'Expired Members'),
    ]
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('in_app', 'In-App'),
        ('both', 'Both'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all_users')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='both')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_announcements'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    class Meta:
        db_table = 'AdminNotifications_announcement'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.status})"