from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Event, EventRegistration
from .serializers import EventRegistrationSerializer

def send_styled_event_email(reg, event, status_type):
    """
    Helper function to send the HTML email.
    """
    try:
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
            'location': getattr(event, 'location', 'N/A'),
            'event_date': getattr(event, 'date', 'TBA'), 
        }

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
    except Exception as e:
        print(f"Email sending failed: {e}")


@api_view(['POST'])
@permission_classes([AllowAny])
# --- ADD THIS DECORATOR TO FIX THE 415 ERROR ---
@parser_classes([MultiPartParser, FormParser, JSONParser])
def register_for_event(request):
    # DRF combines FILES and POST into request.data when parsers are used
    data = request.data 
    
    try:
        event_id = data.get('eventId')
        if not event_id:
            return Response({"error": "eventId is required"}, status=status.HTTP_400_BAD_REQUEST)

        event = Event.objects.get(id=event_id)
        
        # Initial status logic
        is_paid = getattr(event, 'is_paid_event', True)
        initial_status = 'Pending' if is_paid else 'Verified'
        
        # Creating registration
        reg = EventRegistration.objects.create(
            event=event,
            full_name=data.get('fullName'),
            email=data.get('email'),
            phone_number=data.get('phoneNumber'),
            company_name=data.get('companyName', ''),
            attendance_mode=data.get('attendanceMode', 'Physical'),
           
            proof_of_payment=request.FILES.get('proof'), 
            payment_status=initial_status
        )

        # Trigger Email
        email_type = 'VERIFIED' if initial_status == 'Verified' else 'RECEIVED'
        send_styled_event_email(reg, event, email_type)

        return Response({
            "status": "success", 
            "message": "Registration processed successfully.",
            "registration_id": reg.id
        }, status=status.HTTP_201_CREATED)
        
    except Event.DoesNotExist:
        return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Returning the actual error message helps debug the frontend
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
            
            send_styled_event_email(registration, registration.event, 'VERIFIED')
            
            return Response({
                "status": "success", 
                "message": f"Registration for {registration.full_name} verified."
            })
        except EventRegistration.DoesNotExist:
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)