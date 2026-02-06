from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Announcement(models.Model):
    """Model for admin announcements/notifications"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
    ]
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('in_app', 'In-App'),
        ('both', 'Both'),
    ]
    
    AUDIENCE_CHOICES = [
        ('all_users', 'All Users'),
        ('members', 'Members'),
        ('applicants', 'Applicants'),
        ('admins', 'Admins'),
        ('expired_members', 'Expired Members'),
    ]
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    audience = models.CharField(max_length=50, choices=AUDIENCE_CHOICES, default='all_users')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='both')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For scheduled announcements
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Priority level
    priority = models.CharField(
        max_length=20,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
    
    def __str__(self):
        return f"{self.title} - {self.status}"
