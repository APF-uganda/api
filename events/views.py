from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import EventRegistration
from .serializers import EventRegistrationSerializer
from .services import send_event_confirmation

class EventRegistrationViewSet(viewsets.ModelViewSet):
    queryset = EventRegistration.objects.all()
    serializer_class = EventRegistrationSerializer

    def perform_create(self, serializer):
        registration = serializer.save()
        # Trigger the email immediately upon registration
        try:
            send_event_confirmation(registration)
        except Exception as e:
            print(f"Email failed: {e}")