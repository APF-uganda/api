from django.contrib import admin
from .models import Event, EventRegistration

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location')
    search_fields = ('title',)

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    # This shows the most important info in the table list
    list_display = ('full_name', 'email', 'event', 'attendance_mode', 'created_at')
    
    # This adds a sidebar filter so the admin can click an Event name 
    # and instantly see only people for that specific event
    list_filter = ('event', 'attendance_mode', 'created_at')
    
    # Allows the admin to search for a specific person by name or email
    search_fields = ('full_name', 'email')
    
    # Organizes the view when you click into a specific registration
    readonly_fields = ('created_at',)