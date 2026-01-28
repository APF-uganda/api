from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from authentication.permissions import IsAdmin
from .models import ContactMessage
from .serializers import ContactMessageSerializer

@api_view(['GET'])
@permission_classes([AllowAny])
def contacts_root(request):
    """
    Contacts API root endpoint (public)
    """
    return Response({
        'message': 'Contacts API',
        'endpoints': {
            'submit': '/api/contacts/submit/ [POST] - Public',
            'list': '/api/contacts/list/ [GET] - Admin only'
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def create_contact_message(request):
    """
    Create a new contact message (public endpoint)
    
    Security: No authentication required for contact form submission
    """
    serializer = ContactMessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                'message': 'Your message has been sent successfully!',
                'data': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    return Response(
        {
            'message': 'Failed to send message',
            'errors': serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdmin])
def list_contact_messages(request):
    """
    List all contact messages (admin only)
    
    Security: Requires JWT authentication and admin role
    """
    messages = ContactMessage.objects.all().order_by('-created_at')
    serializer = ContactMessageSerializer(messages, many=True)
    return Response(serializer.data)
