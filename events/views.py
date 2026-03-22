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

from .models import EventRegistration
from .serializers import EventRegistrationSerializer

def send_styled_event_email(reg, status_type):
    """
    Helper function using the new model fields (event_title).
    """
    try:
        # Use the title stored directly on the registration object
        event_title = reg.event_title
        
        if status_type == 'RECEIVED':
            subject = f"Registration Received: {event_title}"
            status_text = "Pending Verification"
            message_body = (
                f"We have received your registration for '{event_title}'. "
                "Our team is currently verifying the details. You will receive a final "
                "confirmation email once verified."
            )
        else:
            subject = f"Registration Confirmed: {event_title}"
            status_text = "Confirmed & Verified"
            message_body = (
                f"Great news! Your registration for '{event_title}' has been officially verified. "
                "We look forward to having you join us!"
            )

        context = {
            'user_name': reg.full_name,
            'message_body': message_body,
            'status_text': status_text,
            'event_title': event_title,
            'location': 'As specified in event details',
            'event_date': 'TBA', 
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
@parser_classes([MultiPartParser, FormParser, JSONParser])
def register_for_event(request):
    data = request.data 
    
    try:
        strapi_id = data.get('eventId')
        event_title = data.get('eventTitle')
        
        if not strapi_id or not event_title:
            return Response({"error": "Both eventId and eventTitle are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Logic for Paid vs Free based on presence of a proof file
        proof_file = request.FILES.get('proof')
        initial_status = 'Pending' if proof_file else 'Verified'
        
        # Creating registration using the decoupled model
        reg = EventRegistration.objects.create(
            strapi_event_id=strapi_id,
            event_title=event_title,
            full_name=data.get('fullName'),
            email=data.get('email'),
            phone_number=data.get('phoneNumber'),
            company_name=data.get('companyName', ''),
            proof_of_payment=proof_file, 
            payment_status=initial_status
        )

        # Trigger Email
        email_type = 'VERIFIED' if initial_status == 'Verified' else 'RECEIVED'
        send_styled_event_email(reg, email_type)

        return Response({
            "status": "success", 
            "message": "Registration processed successfully.",
            "registration_id": reg.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
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
            
            send_styled_event_email(registration, 'VERIFIED')
            
            return Response({
                "status": "success", 
                "message": f"Registration for {registration.full_name} verified."
            })
        except EventRegistration.DoesNotExist:
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)