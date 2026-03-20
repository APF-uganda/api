from rest_framework import serializers
from .models import Event, EventRegistration

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

class EventRegistrationSerializer(serializers.ModelSerializer):
    # This pulls the title of the related event for the admin table
    event_title = serializers.ReadOnlyField(source='event.title')
    
    # Ensures the full URL for the image is sent (e.g., http://localhost:8000/media/...)
    proof_of_payment = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = EventRegistration
        fields = [
            'id', 'event', 'event_title', 'full_name', 'email', 
            'phone_number', 'company_name', 'attendance_mode', 
            'proof_of_payment', 'payment_status', 'created_at'
        ]