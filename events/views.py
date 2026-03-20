from django.core.mail import EmailMessage
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, EventRegistration
from .serializers import EventRegistrationSerializer



@csrf_exempt
def register_for_event(request):
    if request.method == 'POST':
        data = request.POST
        files = request.FILES
        
        try:
            event = Event.objects.get(id=data.get('eventId'))
            
           
            initial_status = 'Verified' if not event.is_paid_event else 'Pending'
            
            # Create the Registration record
            reg = EventRegistration.objects.create(
                event=event,
                full_name=data.get('fullName'),
                email=data.get('email'),
                phone_number=data.get('phoneNumber'),
                company_name=data.get('companyName', ''),
                
                attendance_mode=data.get('attendanceMode', 'Physical'),
                proof_of_payment=files.get('proof'),
                payment_status=initial_status
            )

            # 3. Dynamic Email Content
            if event.is_paid_event:
                subject = f"Registration Received: {event.title}"
                body = (
                    f"Hello {reg.full_name},\n\n"
                    f"We have received your registration and proof of payment for '{event.title}'.\n\n"
                    "Our finance team is currently verifying the transaction (Merchant Code: 345678).\n"
                    "You will receive a final confirmation email once verified.\n\n"
                    "Best regards,\nEvents Team"
                )
            else:
                subject = f"Registration Confirmed: {event.title}"
                body = (
                    f"Hello {reg.full_name},\n\n"
                    f"Your registration for '{event.title}' is confirmed!\n"
                    f"Location: {event.location}\n"
                    f"Date: {event.date}\n\n"
                    "We look forward to seeing you there.\n\n"
                    "Best regards,\nEvents Team"
                )
            
            email = EmailMessage(subject, body, settings.EMAIL_HOST_USER, [reg.email])
            email.send(fail_silently=False)

            return JsonResponse({
                "status": "success", 
                "message": "Registration processed successfully.",
                "registration_id": reg.id
            })
            
        except Event.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Event not found"}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)




class AdminRegistrationListView(generics.ListAPIView):
    queryset = EventRegistration.objects.all().order_by('-created_at')
    serializer_class = EventRegistrationSerializer
    permission_classes = [permissions.IsAdminUser]


class VerifyRegistrationView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        try:
            registration = EventRegistration.objects.get(pk=pk)
            registration.payment_status = 'Verified'
            # This triggers the model save() which can send the automated 'Success' email
            registration.save() 
            
            return Response({
                "status": "success", 
                "message": f"Registration for {registration.full_name} verified."
            })
        except EventRegistration.DoesNotExist:
            return Response({"status": "error", "message": "Registration not found"}, status=404)