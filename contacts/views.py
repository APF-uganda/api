from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ContactMessage
from .serializers import ContactMessageSerializer

@api_view(['GET'])
def contacts_root(request):
    """
    Contacts API root endpoint
    """
    return Response({
        'message': 'Contacts API',
        'endpoints': {
            'submit': '/api/contacts/submit/ [POST]',
            'list': '/api/contacts/list/ [GET]'
        }
    })

@api_view(['POST'])
def create_contact_message(request):
    """
    Create a new contact message
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
def list_contact_messages(request):
    """
    List all contact messages (for admin use)
    """
    messages = ContactMessage.objects.all()
    serializer = ContactMessageSerializer(messages, many=True)
    return Response(serializer.data)
