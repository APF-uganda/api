from django.contrib import admin
from .models import MemberDocument


@admin.register(MemberDocument)
class MemberDocumentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'user', 'file_type', 'file_size', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['file_name', 'user__email']
    readonly_fields = ['user', 'file', 'file_name', 'file_size', 'file_type', 'uploaded_at']
