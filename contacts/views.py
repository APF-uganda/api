from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from authentication.permissions import IsAdmin
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
                    "submit": "/api/contacts/submit/ [POST] - Public",
                    "list": "/api/contacts/list/ [GET] - Admin only"
                }
            }
        }
    )},
    tags=['Contacts']
)
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

@swagger_auto_schema(
    method='post',
    operation_description="Submit a contact message (public endpoint - no authentication required)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'email', 'subject', 'message'],
        properties={
            'name': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Full name of the person contacting',
                example='John Doe'
            ),
            'email': openapi.Schema(
                type=openapi.TYPE_STRING,
                format='email',
                description='Email address for response',
                example='john@example.com'
            ),
            'subject': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Subject of the message',
                example='Inquiry about membership'
            ),
            'message': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Detailed message content',
                example='I would like to know more about the membership process.'
            ),
        },
    ),
    responses={
        201: openapi.Response(
            description="Message sent successfully",
            examples={
                "application/json": {
                    "message": "Your message has been sent successfully!",
                    "data": {
                        "id": 1,
                        "name": "John Doe",
                        "email": "john@example.com",
                        "subject": "Inquiry",
                        "message": "Message content",
                        "created_at": "2026-03-02T10:00:00Z"
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Validation error",
            examples={
                "application/json": {
                    "message": "Failed to send message",
                    "errors": {
                        "email": ["Enter a valid email address."]
                    }
                }
            }
        )
    },
    tags=['Contacts']
)
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

@swagger_auto_schema(
    method='get',
    operation_description="List all contact messages (admin only)",
    manual_parameters=[
        openapi.Parameter(
            'Authorization',
            openapi.IN_HEADER,
            description="JWT token (format: Bearer <token>)",
            type=openapi.TYPE_STRING,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="List of contact messages",
            schema=ContactMessageSerializer(many=True),
            examples={
                "application/json": [
                    {
                        "id": 1,
                        "name": "John Doe",
                        "email": "john@example.com",
                        "subject": "Inquiry",
                        "message": "Message content",
                        "created_at": "2026-03-02T10:00:00Z"
                    }
                ]
            }
        ),
        401: "Unauthorized - Authentication required",
        403: "Forbidden - Admin access required"
    },
    tags=['Contacts'],
    security=[{'Bearer': []}]
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
