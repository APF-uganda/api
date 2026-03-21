from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, EventRegistration
from .serializers import EventRegistrationSerializer

def send_styled_event_email(reg, event, status_type):
    """
    Helper function to send the HTML email.
    status_type: 'RECEIVED' or 'VERIFIED'
    """
    if status_type == 'RECEIVED':
        subject = f"Registration Received: {event.title}"
        status_text = "Pending Verification"
        message_body = (
            f"We have received your registration and proof of payment for '{event.title}'. "
            "Our finance team is currently verifying the transaction. You will receive a final "
            "confirmation email once verified."
        )
    else:
        subject = f"Registration Confirmed: {event.title}"
        status_text = "Confirmed & Verified"
        message_body = (
            f"Great news! Your registration for '{event.title}' has been officially verified. "
            "We look forward to having you join us!"
        )

    context = {
        'user_name': reg.full_name,
        'message_body': message_body,
        'status_text': status_text,
        'event_title': event.title,
        'location': event.location,
        'event_date': event.date, # Ensure your model has a 'date' field
    }

    # Load the HTML template you created
    html_content = render_to_string('emails/event_confirmation.html', context)
    text_content = strip_tags(html_content) 

    email = EmailMultiAlternatives(
        subject,
        text_content,
        f"APF Uganda <{settings.EMAIL_HOST_USER}>",
        [reg.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)

@csrf_exempt
def register_for_event(request):
    if request.method == 'POST':
        data = request.POST
        files = request.FILES
        
        try:
            event = Event.objects.get(id=data.get('eventId'))
            initial_status = 'Verified' if not event.is_paid_event else 'Pending'
            
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

            email_type = 'VERIFIED' if not event.is_paid_event else 'RECEIVED'
            send_styled_event_email(reg, event, email_type)

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
            registration.save() 
            
            # --- TRIGGER: Verification Success Email ---
            send_styled_event_email(registration, registration.event, 'VERIFIED')
            
            return Response({
                "status": "success", 
                "message": f"Registration for {registration.full_name} verified and email sent."
            })
        except EventRegistration.DoesNotExist:
            return Response({"status": "error", "message": "Registration not found"}, status=404)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=400)