"""
Analytics and Reports Models
Following SOLID principles with proper separation of concerns
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class ReportTemplate(models.Model):
    """
    Template for different types of reports
    Single Responsibility: Manages report template configuration
    """
    REPORT_TYPES = [
        ('membership', 'Membership Report'),
        ('applications', 'Applications Report'),
        ('financial', 'Financial Report'),
        ('events', 'Events Report'),
        ('compliance', 'Compliance Report'),
        ('growth', 'Growth Analysis Report'),
        ('custom', 'Custom Report'),
    ]
    
    OUTPUT_FORMATS = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    description = models.TextField()
    output_format = models.CharField(max_length=20, choices=OUTPUT_FORMATS, default='pdf')
    
    # Template configuration
    fields_to_include = models.JSONField(default=list, help_text="List of fields to include in report")
    filters = models.JSONField(default=dict, help_text="Default filters for the report")
    chart_configs = models.JSONField(default=dict, help_text="Chart configuration for visualizations")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_report_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_system_template = models.BooleanField(default=False, help_text="System-generated template")
    
    class Meta:
        db_table = 'reports_template'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class GeneratedReport(models.Model):
    """
    Tracks generated reports and their metadata
    Single Responsibility: Manages generated report instances
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='generated_reports')
    
    # Report details
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Generation parameters
    date_range_start = models.DateTimeField(null=True, blank=True)
    date_range_end = models.DateTimeField(null=True, blank=True)
    filters_applied = models.JSONField(default=dict, help_text="Filters applied during generation")
    parameters = models.JSONField(default=dict, help_text="Additional parameters used")
    
    # File information
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    file_format = models.CharField(max_length=20)
    
    # Processing information
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_duration = models.DurationField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Metadata
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'reports_generated'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['generated_by']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['template']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    @property
    def is_expired(self):
        """Check if report has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0


class AnalyticsMetric(models.Model):
    """
    Stores calculated analytics metrics for caching and historical tracking
    Single Responsibility: Manages analytics metric storage and retrieval
    """
    METRIC_TYPES = [
        ('count', 'Count'),
        ('percentage', 'Percentage'),
        ('average', 'Average'),
        ('sum', 'Sum'),
        ('ratio', 'Ratio'),
        ('growth_rate', 'Growth Rate'),
    ]
    
    METRIC_CATEGORIES = [
        ('membership', 'Membership'),
        ('applications', 'Applications'),
        ('system', 'System'),
        ('engagement', 'Engagement'),
        ('performance', 'Performance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Metric identification
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=METRIC_CATEGORIES)
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    
    # Metric value and metadata
    value = models.DecimalField(max_digits=15, decimal_places=4)
    unit = models.CharField(max_length=50, blank=True, help_text="Unit of measurement")
    
    # Time period information
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    period_type = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ])
    
    # Additional context
    filters = models.JSONField(default=dict, help_text="Filters applied when calculating metric")
    metadata = models.JSONField(default=dict, help_text="Additional metric metadata")
    
    # Tracking
    calculated_at = models.DateTimeField(auto_now_add=True)
    calculated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'reports_analytics_metric'
        ordering = ['-calculated_at']
        indexes = [
            models.Index(fields=['category', 'name']),
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['calculated_at']),
        ]
        unique_together = ['name', 'category', 'period_start', 'period_end']
    
    def __str__(self):
        return f"{self.name} ({self.category}): {self.value} {self.unit}"


class ReportSchedule(models.Model):
    """
    Manages scheduled report generation
    Single Responsibility: Handles report scheduling and automation
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='schedules')
    
    # Schedule configuration
    name = models.CharField(max_length=200)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    is_active = models.BooleanField(default=True)
    
    # Recipients
    recipients = models.JSONField(default=list, help_text="List of email addresses to send reports to")
    
    # Timing
    next_run_at = models.DateTimeField()
    last_run_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_schedules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reports_schedule'
        ordering = ['next_run_at']
        indexes = [
            models.Index(fields=['is_active', 'next_run_at']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"