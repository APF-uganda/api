from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class UserProfileViewSet(viewsets.ViewSet):
    """
    ViewSet for user profile management (consolidated from profiles app)
    Handles profile operations for the authenticated user
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Get current user's profile information",
        responses={200: openapi.Response(description="User profile data")}
    )
    def me(self, request):
        """Get current user's profile"""
        user = request.user
        data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
            'profile_picture': user.profile_picture.url if user.profile_picture else None,
            'is_profile_complete': user.is_profile_complete,
        }
        return Response(data)

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Update current user's profile information",
        responses={200: openapi.Response(description="Profile updated successfully")}
    )
    def update(self, request):
        """Update current user's profile"""
        user = request.user
        data = request.data
        
        allowed_fields = [
            'first_name', 'last_name', 'middle_name', 'phone_number', 'alternative_phone',
            'date_of_birth', 'gender', 'address_line_1', 'address_line_2', 'city',
            'state_province', 'postal_code', 'country', 'job_title', 'organization',
            'department', 'icpau_registration_number', 'practising_status',
            'membership_category', 'years_of_experience', 'specializations',
            'bio', 'website', 'linkedin_profile', 'preferred_language', 'timezone',
            'profile_visibility', 'show_email', 'show_phone',
            'email_notifications', 'sms_notifications', 'newsletter_subscription',
            'event_notifications'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.save()
        return Response({'message': 'Profile updated successfully'})

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Upload profile picture",
        responses={200: openapi.Response(description="Profile picture uploaded successfully")}
    )
    @action(detail=False, methods=['post'])
    def upload_picture(self, request):
        """Upload profile picture"""
        if 'profile_picture' not in request.FILES:
            return Response({'error': 'No file provided'}, status=400)
        
        file = request.FILES['profile_picture']
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if file.content_type not in allowed_types:
            return Response({'error': 'Invalid file type. Only JPEG, PNG, and GIF are allowed.'}, status=400)
        
        user = request.user
        user.profile_picture = file
        user.save()
        
        return Response({
            'message': 'Profile picture uploaded successfully',
            'profile_picture': user.profile_picture.url if user.profile_picture else None
        })

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Remove profile picture",
        responses={200: openapi.Response(description="Profile picture removed successfully")}
    )
    @action(detail=False, methods=['delete'])
    def remove_picture(self, request):
        """Remove profile picture"""
        user = request.user
        if user.profile_picture:
            user.profile_picture.delete()
            user.profile_picture = None
            user.save()
        
        return Response({'message': 'Profile picture removed successfully'})

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Update privacy settings",
        methods=['put', 'patch'],
        responses={200: openapi.Response(description="Privacy settings updated successfully")}
    )
    @action(detail=False, methods=['put', 'patch'])
    def privacy_settings(self, request):
        """Update privacy settings"""
        user = request.user
        data = request.data
        
        privacy_fields = ['profile_visibility', 'show_email', 'show_phone']
        for field in privacy_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.save()
        return Response({'message': 'Privacy settings updated successfully'})

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Update notification preferences",
        methods=['put', 'patch'],
        responses={200: openapi.Response(description="Notification preferences updated successfully")}
    )
    @action(detail=False, methods=['put', 'patch'])
    def notification_preferences(self, request):
        """Update notification preferences"""
        user = request.user
        data = request.data
        
        notification_fields = ['email_notifications', 'sms_notifications', 'newsletter_subscription', 'event_notifications']
        for field in notification_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.save()
        return Response({'message': 'Notification preferences updated successfully'})

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Get profile completion status",
        responses={200: openapi.Response(description="Profile completion status")}
    )
    @action(detail=False, methods=['get'])
    def completion_status(self, request):
        """Get profile completion status"""
        user = request.user
        
        required_fields = ['first_name', 'last_name', 'phone_number', 'city', 'country']
        professional_fields = ['job_title', 'organization']
        
        missing_required = [field for field in required_fields if not getattr(user, field)]
        missing_professional = [field for field in professional_fields if not getattr(user, field)]
        
        total_fields = len(required_fields) + len(professional_fields)
        filled_fields = total_fields - len(missing_required) - len(missing_professional)
        completion_percentage = int((filled_fields / total_fields) * 100) if total_fields > 0 else 0
        
        return Response({
            'is_complete': user.is_profile_complete,
            'completion_percentage': completion_percentage,
            'missing_fields': missing_required + missing_professional
        })

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Get user activity log",
        responses={200: openapi.Response(description="User activity log")}
    )
    @action(detail=False, methods=['get'])
    def activity_log(self, request):
        """Get user activity log"""
        return Response([])
