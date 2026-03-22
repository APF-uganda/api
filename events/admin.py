from django.contrib import admin
from django.utils.html import format_html
from .models import EventRegistration

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 
        'event_title', 
        'location',      
        'event_date',    
        'payment_status', 
        'display_proof', 
        'created_at'
    )
    
    # Filter by location and title to help sort attendees
    list_filter = ('event_title', 'location', 'payment_status', 'created_at')
    
    # Search by location as well
    search_fields = ('full_name', 'email', 'event_title', 'location', 'strapi_event_id')
    
    actions = ['mark_as_verified']

    def display_proof(self, obj):
        if obj.proof_of_payment:
            return format_html(
                '<a href="{0}" target="_blank" style="color: #264b5d; font-weight: bold;">View Receipt</a>', 
                obj.proof_of_payment.url
            )
        return "No Receipt"
    display_proof.short_description = "Payment Proof"

    @admin.action(description="Verify selected registrations")
    def mark_as_verified(self, request, queryset):
        
        count = queryset.update(payment_status='Verified')
        self.message_user(request, f"{count} registrations were successfully verified.")