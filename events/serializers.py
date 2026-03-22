from rest_framework import serializers
from .models import EventRegistration

class EventRegistrationSerializer(serializers.ModelSerializer):
    strapi_event_id = serializers.CharField(required=True)
    event_title = serializers.CharField(required=True)
    
    proof_of_payment = serializers.ImageField(
        required=False, 
        allow_null=True
    )

    class Meta:
        model = EventRegistration
        fields = [
            'id', 
            'strapi_event_id', 
            'event_title', 
            'event_date',
            'location', 
            'full_name', 
            'email', 
            'phone_number', 
            'company_name', 
            'proof_of_payment', 
            'payment_status', 
            'admin_notes',
            'created_at'
        ]
        
        read_only_fields = ['id', 'created_at', 'payment_status', 'admin_notes']

    def validate_email(self, value):
        return value.lower().strip()