from django.contrib import admin
from .models import ReportTemplate, GeneratedReport

@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'output_format', 'created_at')
    search_fields = ('name', 'report_type')
    list_filter = ('report_type', 'output_format')

@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'template', 'status', 'file_format', 'created_at')
    list_filter = ('status', 'file_format')
    readonly_fields = ('file_path', 'file_size', 'processing_duration', 'error_message')