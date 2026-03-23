from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# PDF Generation imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from .models import EventRegistration
from .serializers import EventRegistrationSerializer

from datetime import datetime 

def send_styled_event_email(reg, status_type):
    try:
        event_title = reg.event_title
        
        # --- FIX 1: DATE FORMATTING ---
        raw_date = reg.event_date
        display_date = "Date specified in event details"
        
        if raw_date:
            try:
              
                date_obj = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                display_date = date_obj.strftime('%B %d, %Y') 
            except:
                display_date = str(raw_date) # Fallback

        
        event_location = reg.location if reg.location and reg.location != "undefined" else "Main Event Hall (Kampala)"
        
        if status_type == 'RECEIVED':
            subject = f"Registration Received: {event_title}"
            status_text = "Pending Verification"
            message_body = (
                f"We have received your registration for '{event_title}'. "
                "Our team is currently verifying your payment/details."
            )
        else:
            subject = f"Registration Confirmed: {event_title}"
            status_text = "Confirmed & Verified"
            message_body = f"Great news! Your registration for '{event_title}' has been verified."

        context = {
            'user_name': reg.full_name,
            'message_body': message_body,
            'status_text': status_text,
            'event_title': event_title,
            'event_date': display_date, 
            'location': event_location,  
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
        # 1. Capture IDs and Titles
        strapi_id = data.get('strapi_event_id') or data.get('eventId')
        event_title = data.get('event_title') or data.get('eventTitle')
        event_date = data.get('event_date') or data.get('eventDate')
        
        # 2. Capture Location accurately
      
        event_location = data.get('location') or data.get('event_location') or data.get('eventlocation')
        
        if not strapi_id or not event_title:
            return Response(
                {"error": "Both eventId and eventTitle are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Handle file upload
        proof_file = request.FILES.get('proof_of_payment') or request.FILES.get('proof')
        initial_status = 'Pending' if proof_file else 'Verified'
        
        # 4. Create record using the variables defined above
        reg = EventRegistration.objects.create(
            strapi_event_id=strapi_id,
            event_title=event_title,
            event_date=event_date,
            location=event_location,  
            full_name=data.get('full_name') or data.get('fullName'),
            email=data.get('email'),
            phone_number=data.get('phone_number') or data.get('phoneNumber'),
            company_name=data.get('company_name') or data.get('companyName', ''),
            proof_of_payment=proof_file, 
            payment_status=initial_status
        )

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
    serializer_class = EventRegistrationSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = EventRegistration.objects.all().order_by('-created_at')
        # Updated to handle filtering by Event Title/Search
        search_query = self.request.query_params.get('event_title', None)
        if search_query:
            queryset = queryset.filter(
                Q(event_title__icontains=search_query) | 
                Q(full_name__icontains=search_query) |
                Q(event_date__icontains=search_query)
            )
        return queryset




@api_view(['GET'])
@permission_classes([AllowAny]) 
def export_registrations_pdf(request):
   
    token_str = request.query_params.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    
   
    try:
        validated_token = AccessToken(token_str)
       
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=validated_token['user_id'])
        if not user.is_staff:
            return HttpResponse("Unauthorized", status=401)
    except Exception:
        return HttpResponse("Unauthorized or Expired Session", status=401)

    search_query = request.query_params.get('event_title', '')
    
    regs = EventRegistration.objects.all().order_by('-created_at')
    if search_query:
        regs = regs.filter(
            Q(event_title__icontains=search_query) | 
            Q(event_date__icontains=search_query)
        )

    response = HttpResponse(content_type='application/pdf')
    filename = f"Registrations_{search_query or 'All'}.pdf".replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Event Registrations")
    
    # Header logic
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, "APF Uganda Event Registration List")
    p.setFont("Helvetica", 10)
    p.drawString(50, 735, f"Filter: {search_query if search_query else 'All'}")
    p.drawString(50, 720, f"Total Count: {regs.count()}")
    p.line(50, 710, 550, 710)

    # Table Headers
    p.setFont("Helvetica-Bold", 10)
    y = 690
    p.drawString(50, y, "Attendee Name")
    p.drawString(200, y, "Event")
    p.drawString(400, y, "Status")
    p.drawString(480, y, "Date")

    # Rows
    p.setFont("Helvetica", 8)
    y -= 20
    for reg in regs:
        if y < 50:
            p.showPage()
            y = 750
        p.drawString(50, y, str(reg.full_name)[:30])
        p.drawString(200, y, str(reg.event_title)[:45])
        p.drawString(400, y, str(reg.payment_status))
        p.drawString(480, y, str(reg.event_date)[:15])
        y -= 15

    p.showPage()
    p.save()
    return response


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