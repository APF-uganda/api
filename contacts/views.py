from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from authentication.permissions import IsAdmin
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import ContactMessage
from .serializers import ContactMessageSerializer


@swagger_auto_schema(
    method='get',
    operation_description="Contacts API root endpoint - Lists available endpoints",
    responses={200: openapi.Response(
        description="API information",
        examples={
            "application/json": {
                "message": "Contacts API",
                "endpoints": {
                    "submit": "/api/v1/contacts/submit/ [POST] - Public",
                    "list": "/api/v1/contacts/list/ [GET] - Admin only",
                    "toggle_read": "/api/v1/contacts/<id>/toggle-read/ [PATCH] - Admin only",
                    "delete": "/api/v1/contacts/<id>/delete/ [DELETE] - Admin only"
                }
            }
        }
    )},
    tags=['Contacts']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def contacts_root(request):
    """Contacts API root endpoint (public)"""
    return Response({
        'message': 'Contacts API',
        'endpoints': {
            'submit': '/api/v1/contacts/submit/ [POST] - Public',
            'list': '/api/v1/contacts/list/ [GET] - Admin only',
            'toggle_read': '/api/v1/contacts/<id>/toggle-read/ [PATCH]',
            'delete': '/api/v1/contacts/<id>/delete/ [DELETE]'
        }
    })



@swagger_auto_schema(
    method='post',
    operation_description="Submit a contact message (public endpoint)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'email', 'subject', 'message'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, example='John Doe'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', example='john@example.com'),
            'subject': openapi.Schema(type=openapi.TYPE_STRING, example='Inquiry about membership'),
            'message': openapi.Schema(type=openapi.TYPE_STRING, example='I would like to know more.'),
        },
    ),
    responses={
        201: openapi.Response(description="Message sent successfully"),
        400: openapi.Response(description="Validation error")
    },
    tags=['Contacts']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def create_contact_message(request):
    """Create a new contact message (public)"""
    serializer = ContactMessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {'message': 'Your message has been sent successfully!', 'data': serializer.data},
            status=status.HTTP_201_CREATED
        )
    return Response(
        {'message': 'Failed to send message', 'errors': serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )



@swagger_auto_schema(
    method='get',
    operation_description="List all contact messages (admin only)",
    responses={200: ContactMessageSerializer(many=True)},
    tags=['Contacts'],
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdmin])
def list_contact_messages(request):
    """List all contact messages (admin only)"""
    messages = ContactMessage.objects.all().order_by('-created_at')
    serializer = ContactMessageSerializer(messages, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='patch',
    operation_description="Toggle the read status of a message (admin only)",
    responses={200: openapi.Response(description="Status updated")},
    tags=['Contacts'],
    security=[{'Bearer': []}]
)
@api_view(['PATCH'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdmin])
def toggle_message_read_status(request, pk):
    """Mark a message as read or unread"""
    message = get_object_or_404(ContactMessage, pk=pk)
    message.is_read = not message.is_read
    message.save()
    return Response({
        'status': 'success',
        'is_read': message.is_read,
        'message': f"Message marked as {'read' if message.is_read else 'unread'}."
    }, status=status.HTTP_200_OK)



@swagger_auto_schema(
    method='delete',
    operation_description="Delete an inquiry (admin only)",
    responses={204: "Deleted successfully"},
    tags=['Contacts'],
    security=[{'Bearer': []}]
)
@api_view(['DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdmin])
def delete_contact_message(request, pk):
    """Delete a contact message permanently"""
    message = get_object_or_404(ContactMessage, pk=pk)
    message.delete()
    return Response({'message': 'Inquiry deleted successfully'}, status=status.HTTP_204_NO_CONTENT)