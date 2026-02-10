from django.contrib import admin
from .models import Application
from Documents.models import Document


class DocumentInline(admin.TabularInline):
    """
    Inline admin for viewing uploaded documents within an application.
    """
    model = Document
    extra = 0
    readonly_fields = ['file_name', 'file_size', 'file_type', 'uploaded_at', 'file']
    fields = ['file', 'file_name', 'file_size', 'file_type', 'uploaded_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        """Prevent adding documents through admin interface."""
        return False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    Custom admin interface for managing membership applications.
    Provides comprehensive view with search, filtering, organized fieldsets,
    and bulk actions for approval workflow.
    """
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'payment_method',
        'payment_status',
        'status',
        'submitted_at'
    ]
    list_filter = ['status', 'payment_method', 'payment_status', 'submitted_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['submitted_at', 'updated_at', 'password_hash']
    inlines = [DocumentInline]

    # Allow inline editing of status in list view
    list_editable = ['status']

    # Bulk actions
    actions = ["approve_applications", "reject_applications", "reset_applications"]

    def approve_applications(self, request, queryset):
        from . import services
        for application in queryset:
            services.approve_application(application.id)
    approve_applications.short_description = "Approve selected applications"

    def reject_applications(self, request, queryset):
        from . import services
        for application in queryset:
            services.reject_application(application.id)
    reject_applications.short_description = "Reject selected applications"

    def reset_applications(self, request, queryset):
        from . import services
        for application in queryset:
            services.retry_application(application.id)
    reset_applications.short_description = "Reset selected applications to pending"

    fieldsets = [
        ('Account Information', {
            'fields': ['username', 'email', 'password_hash']
        }),
        ('Personal Information', {
            'fields': ['first_name', 'last_name', 'date_of_birth', 'phone_number', 'address']
        }),
        ('Payment Information', {
            'fields': [
                'payment_method',
                'payment_phone',
                'payment_card_number',
                'payment_card_expiry',
                'payment_card_cvv',
                'payment_cardholder_name',
                'payment_status',
                'payment_transaction_reference',
                'payment_error_message'
            ]
        }),
        ('Status', {
            'fields': ['status', 'submitted_at', 'updated_at']
        })
    ]

    def get_readonly_fields(self, request, obj=None):
        """
        Make all fields except status readonly for existing applications.
        Prevents accidental modification of submitted application data.
        """
        if obj:  # Editing an existing object
            return self.readonly_fields + [
                'username', 'email', 'first_name', 'last_name',
                'date_of_birth', 'phone_number', 'address',
                'payment_method', 'payment_phone',
                'payment_card_number', 'payment_card_expiry', 'payment_card_cvv',
                'payment_cardholder_name', 'payment_status',
                'payment_transaction_reference', 'payment_error_message'
            ]
        return self.readonly_fields


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing documents.
    Primarily accessed through ApplicationAdmin inline.
    """
    list_display = ['file_name', 'application', 'file_type', 'file_size', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['file_name', 'application__username', 'application__email']
    readonly_fields = ['application', 'file', 'file_name', 'file_size', 'file_type', 'uploaded_at']
    
    def has_add_permission(self, request):
        """Prevent adding documents through admin interface."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting documents through admin interface."""
        return False
