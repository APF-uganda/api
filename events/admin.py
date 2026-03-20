from django.contrib import admin
from django.utils.html import format_html
from .models import Event, EventRegistration

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'event', 'attendance_mode', 'payment_status', 'display_proof', 'created_at')
    list_filter = ('event', 'payment_status', 'attendance_mode')
    search_fields = ('full_name', 'email')
    actions = ['mark_as_verified']

    # Makes the proof clickable and visible in the list
    def display_proof(self, obj):
        if obj.proof_of_payment:
            return format_html('<a href="{0}" target="_blank">View Receipt</a>', obj.proof_of_payment.url)
        return "No Receipt"
    display_proof.short_description = "Payment Proof"

    # Bulk action to verify members
    def mark_as_verified(self, request, queryset):
        queryset.update(payment_status='Verified')
        # You could also trigger a "Verification Email" here for all selected users
    mark_as_verified.short_description = "Verify selected registrations"

admin.site.register(Event)