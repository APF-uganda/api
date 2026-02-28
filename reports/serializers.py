"""
Serializers for Reports and Analytics
Following SOLID principles with proper data validation
"""

from rest_framework import serializers
from .models import ReportTemplate, GeneratedReport, AnalyticsMetric, ReportSchedule


class ReportTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for ReportTemplate model
    Single Responsibility: Handles report template serialization
    """
    created_by_name = serializers.CharField(source='created_by.email', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    output_format_display = serializers.CharField(source='get_output_format_display', read_only=True)
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'report_type', 'report_type_display',
            'description', 'output_format', 'output_format_display',
            'fields_to_include', 'filters', 'chart_configs',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'is_active', 'is_system_template'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def validate_fields_to_include(self, value):
        """Validate fields_to_include is a list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("fields_to_include must be a list")
        return value
    
    def validate_filters(self, value):
        """Validate filters is a dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("filters must be a dictionary")
        return value
    
    def validate_chart_configs(self, value):
        """Validate chart_configs is a dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("chart_configs must be a dictionary")
        return value


class GeneratedReportSerializer(serializers.ModelSerializer):
    """
    Serializer for GeneratedReport model
    Single Responsibility: Handles generated report serialization
    """
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.report_type', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedReport
        fields = [
            'id', 'template', 'template_name', 'template_type',
            'title', 'description', 'status', 'status_display',
            'date_range_start', 'date_range_end', 'filters_applied', 'parameters',
            'file_path', 'file_size', 'file_size_mb', 'file_format',
            'processing_started_at', 'processing_completed_at', 'processing_duration',
            'error_message', 'generated_by', 'generated_by_name',
            'created_at', 'expires_at', 'is_expired',
            'download_count', 'last_downloaded_at', 'download_url'
        ]
        read_only_fields = [
            'id', 'processing_started_at', 'processing_completed_at',
            'processing_duration', 'error_message', 'generated_by',
            'created_at', 'download_count', 'last_downloaded_at'
        ]
    
    def get_download_url(self, obj):
        """Generate the download URL for the report"""
        if obj.status == 'completed' and obj.file_path:
            return f'/api/v1/reports/download/{obj.id}/'
        return None


class AnalyticsMetricSerializer(serializers.ModelSerializer):
    """
    Serializer for AnalyticsMetric model
    Single Responsibility: Handles analytics metric serialization
    """
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)
    calculated_by_name = serializers.CharField(source='calculated_by.email', read_only=True)
    
    class Meta:
        model = AnalyticsMetric
        fields = [
            'id', 'name', 'category', 'category_display',
            'metric_type', 'metric_type_display', 'value', 'unit',
            'period_start', 'period_end', 'period_type', 'period_type_display',
            'filters', 'metadata', 'calculated_at', 'calculated_by', 'calculated_by_name'
        ]
        read_only_fields = ['id', 'calculated_at', 'calculated_by']
    
    def validate_value(self, value):
        """Validate metric value is numeric"""
        if value is None:
            raise serializers.ValidationError("Value cannot be null")
        return value
    
    def validate_period_dates(self, attrs):
        """Validate period start is before period end"""
        period_start = attrs.get('period_start')
        period_end = attrs.get('period_end')
        
        if period_start and period_end and period_start >= period_end:
            raise serializers.ValidationError(
                "Period start must be before period end"
            )
        
        return attrs


class ReportScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for ReportSchedule model
    Single Responsibility: Handles report schedule serialization
    """
    template_name = serializers.CharField(source='template.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.email', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'template', 'template_name', 'name', 'frequency', 'frequency_display',
            'is_active', 'recipients', 'next_run_at', 'last_run_at',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'last_run_at']
    
    def validate_recipients(self, value):
        """Validate recipients is a list of email addresses"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Recipients must be a list")
        
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for email in value:
            if not isinstance(email, str) or not re.match(email_pattern, email):
                raise serializers.ValidationError(f"Invalid email address: {email}")
        
        return value


class ChartDataSerializer(serializers.Serializer):
    """
    Serializer for chart data responses
    Single Responsibility: Handles chart data serialization
    """
    labels = serializers.ListField(child=serializers.CharField())
    data = serializers.ListField(child=serializers.FloatField())
    title = serializers.CharField()
    generated_at = serializers.DateTimeField(read_only=True)
    
    def validate_data_consistency(self, attrs):
        """Validate labels and data have same length"""
        labels = attrs.get('labels', [])
        data = attrs.get('data', [])
        
        if len(labels) != len(data):
            raise serializers.ValidationError(
                "Labels and data must have the same length"
            )
        
        return attrs


class AnalyticsSummarySerializer(serializers.Serializer):
    """
    Serializer for analytics summary responses
    Single Responsibility: Handles analytics summary serialization
    """
    membership = serializers.DictField()
    applications = serializers.DictField()
    system = serializers.DictField()
    period = serializers.DictField()
    generated_at = serializers.DateTimeField(read_only=True)


class DashboardSummarySerializer(serializers.Serializer):
    """
    Serializer for dashboard summary responses
    Single Responsibility: Handles dashboard summary serialization
    """
    key_metrics = serializers.DictField()
    recent_activity = serializers.DictField()
    trends = serializers.DictField()
    generated_at = serializers.DateTimeField(read_only=True)


class HealthCheckSerializer(serializers.Serializer):
    """
    Serializer for health check responses
    Single Responsibility: Handles health check serialization
    """
    overall_status = serializers.CharField()
    services = serializers.DictField()
    cache_status = serializers.CharField()
    checked_at = serializers.DateTimeField(read_only=True)


class CacheStatsSerializer(serializers.Serializer):
    """
    Serializer for cache statistics responses
    Single Responsibility: Handles cache stats serialization
    """
    cache_size = serializers.IntegerField()
    cache_timeout = serializers.IntegerField()
    cache_type = serializers.CharField()