"""
Views for managing user email notification preferences
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


@swagger_auto_schema(
    method='get',
    operation_description="Get current user's email notification preferences",
    responses={
        200: openapi.Response(
            description="Email preferences retrieved successfully",
            examples={
                "application/json": {
                    "email_notifications_enabled": True,
                    "email_new_posts": True,
                    "email_new_comments": True,
                    "email_post_replies": True,
                    "email_digest_frequency": "weekly"
                }
            }
        )
    },
    tags=['User Profile']
)
@swagger_auto_schema(
    method='put',
    operation_description="Update user's email notification preferences",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'email_notifications_enabled': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Master toggle for all email notifications'),
            'email_new_posts': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Receive emails for new forum posts'),
            'email_new_comments': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Receive emails for new comments'),
            'email_post_replies': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Receive emails when someone replies to your posts'),
            'email_digest_frequency': openapi.Schema(type=openapi.TYPE_STRING, enum=['none', 'daily', 'weekly'], description='Digest email frequency'),
        }
    ),
    responses={
        200: openapi.Response(
            description="Preferences updated successfully",
            examples={
                "application/json": {
                    "message": "Email preferences updated successfully",
                    "preferences": {
                        "email_notifications_enabled": True,
                        "email_new_posts": False,
                        "email_new_comments": True,
                        "email_post_replies": True,
                        "email_digest_frequency": "daily"
                    }
                }
            }
        ),
        400: "Bad Request - Invalid data"
    },
    tags=['User Profile']
)
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def email_preferences(request):
    """
    Get or update user's email notification preferences
    """
    user = request.user
    
    if request.method == 'GET':
        # Return current preferences
        preferences = {
            'email_notifications_enabled': user.email_notifications_enabled,
            'email_new_posts': user.email_new_posts,
            'email_new_comments': user.email_new_comments,
            'email_post_replies': user.email_post_replies,
            'email_digest_frequency': user.email_digest_frequency,
        }
        return Response(preferences)
    
    elif request.method == 'PUT':
        # Update preferences
        data = request.data
        
        # Update fields if provided
        if 'email_notifications_enabled' in data:
            user.email_notifications_enabled = data['email_notifications_enabled']
        if 'email_new_posts' in data:
            user.email_new_posts = data['email_new_posts']
        if 'email_new_comments' in data:
            user.email_new_comments = data['email_new_comments']
        if 'email_post_replies' in data:
            user.email_post_replies = data['email_post_replies']
        if 'email_digest_frequency' in data:
            if data['email_digest_frequency'] in ['none', 'daily', 'weekly']:
                user.email_digest_frequency = data['email_digest_frequency']
            else:
                return Response(
                    {'error': 'Invalid digest frequency. Must be none, daily, or weekly'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        user.save()
        
        preferences = {
            'email_notifications_enabled': user.email_notifications_enabled,
            'email_new_posts': user.email_new_posts,
            'email_new_comments': user.email_new_comments,
            'email_post_replies': user.email_post_replies,
            'email_digest_frequency': user.email_digest_frequency,
        }
        
        return Response({
            'message': 'Email preferences updated successfully',
            'preferences': preferences
        })
