from django.db import models
from django.conf import settings
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