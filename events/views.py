from django.core.mail import EmailMessage
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, EventRegistration
from .serializers import EventRegistrationSerializer

# --- PUBLIC REGISTRATION VIEW ---

@csrf_exempt
def register_for_event(request):
    """
    Handles the initial registration from the React frontend.
    Saves the proof of payment and sends the 'Wait for verification' email.
    """
    if request.method == 'POST':
        data = request.POST
        files = request.FILES
        
        try:
            # 1. Fetch the correct event
            event = Event.objects.get(id=data.get('eventId'))
            
            # 2. Create the Registration record
            reg = EventRegistration.objects.create(
                event=event,
                full_name=data.get('fullName'),
                email=data.get('email'),
                phone_number=data.get('phoneNumber'),
                company_name=data.get('companyName', ''),
                attendance_mode=data.get('attendanceMode', 'Physical'),
                proof_of_payment=files.get('proof'),
                payment_status='Pending'
            )

            # 3. Send the "Received" Email immediately via Gmail
            subject = f"Registration Received: {event.title}"
            body = (
                f"Hello {reg.full_name},\n\n"
                f"We have received your registration and proof of payment for '{event.title}'.\n\n"
                "Our finance team is currently verifying the transaction (Merchant Code: 345678).\n"
                "You will receive a final confirmation email once verified.\n\n"
                "Best regards,\nEvents Team"
            )
            
            email = EmailMessage(
                subject, 
                body, 
                settings.EMAIL_HOST_USER, 
                [reg.email]
            )
            email.send(fail_silently=False)

            return JsonResponse({
                "status": "success", 
                "message": "Registration submitted. Verification email sent.",
                "registration_id": reg.id
            })
            
        except Event.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Event not found"}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# --- ADMIN DASHBOARD VIEWS ---

class AdminRegistrationListView(generics.ListAPIView):
    """
    Returns a list of all registrations for the React Admin Dashboard.
    Sorted by newest first.
    """
    queryset = EventRegistration.objects.all().order_by('-created_at')
    serializer_class = EventRegistrationSerializer
    permission_classes = [permissions.IsAdminUser] # Only Staff/Admins can see this


class VerifyRegistrationView(APIView):
    """
    Endpoint for the admin to click 'Verify'.
    Updates status to 'Verified' and triggers the automated confirmation email.
    """
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        try:
            registration = EventRegistration.objects.get(pk=pk)
            
            # Update the status
            registration.payment_status = 'Verified'
            
            # The model's save() method (discussed earlier) will trigger the 
            # 'Verified' email automatically when this is saved.
            registration.save() 
            
            return Response({
                "status": "success", 
                "message": f"Registration for {registration.full_name} verified."
            })
        except EventRegistration.DoesNotExist:
            return Response({"status": "error", "message": "Registration not found"}, status=404)