from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class JWTAuthenticationAllowInactive(JWTAuthentication):
    """JWT authentication that allows inactive (suspended) users through."""
    def get_user(self, validated_token):
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.settings import api_settings
        User = get_user_model()
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
            return user  # Return user regardless of is_active
        except Exception:
            return None


class IsAuthenticatedOrSuspended(BasePermission):
    """Allow access to authenticated users including suspended (inactive) ones."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.pk)


class UserProfileViewSet(viewsets.ViewSet):
    """
    ViewSet for user profile management (consolidated from profiles app)
    Handles profile operations for the authenticated user
    """
    permission_classes = [IsAuthenticatedOrSuspended]
    authentication_classes = [JWTAuthenticationAllowInactive]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _get_profile_picture_url(self, request, user):
        profile_picture = getattr(user, "profile_picture", None)
        if not profile_picture:
            return None
        try:
            return request.build_absolute_uri(profile_picture.url)
        except Exception:
            return None

    def _serialize_user(self, request, user):
        picture_url = self._get_profile_picture_url(request, user)

        # Suspension info
        suspension_info = None
        if not user.is_active:
            try:
                rec = user.suspension_record
                if rec.reactivated_at is None:
                    suspension_info = {
                        'is_suspended': True,
                        'suspension_type': rec.suspension_type,
                        'reason': rec.suspension_reason,
                        'suspended_at': rec.suspended_at.strftime('%d %B %Y') if rec.suspended_at else '',
                    }
            except Exception:
                suspension_info = {'is_suspended': True, 'suspension_type': 'non_payment', 'reason': '', 'suspended_at': ''}

        return {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'initials': user.initials,
            'profile_picture_url': picture_url,
            'profile_picture': picture_url,
            'user_role': str(user.role),
            'role': str(user.role),
            'is_active': user.is_active,
            'suspension': suspension_info,
            'date_joined': user.created_at,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'middle_name': user.middle_name,
            'date_of_birth': user.date_of_birth,
            'gender': user.gender,
            'phone_number': user.phone_number,
            'alternative_phone': user.alternative_phone,
            'address_line_1': user.address_line_1,
            'address_line_2': user.address_line_2,
            'city': user.city,
            'state_province': user.state_province,
            'postal_code': user.postal_code,
            'country': user.country,
            'job_title': user.job_title,
            'organization': user.organization,
            'department': user.department,
            'icpau_registration_number': user.icpau_registration_number,
            'years_of_experience': user.years_of_experience,
            'specializations': user.specializations,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
        }

    def _update_profile(self, request):
        user = request.user
        data = request.data

        allowed_fields = [
            'first_name', 'last_name', 'middle_name', 'phone_number', 'alternative_phone',
            'date_of_birth', 'gender', 'address_line_1', 'address_line_2', 'city',
            'state_province', 'postal_code', 'country', 'job_title', 'organization',
            'department', 'icpau_registration_number', 'practising_status',
            'membership_category', 'years_of_experience', 'specializations',
        ]

        boolean_fields = set()

        def to_bool(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {'true', '1', 'yes', 'on'}
            return bool(value)

        for field in allowed_fields:
            if field not in data:
                continue

            value = data[field]
            if field in boolean_fields:
                value = to_bool(value)
            elif field == 'years_of_experience':
                if value in (None, ''):
                    value = None
                else:
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        return Response(
                            {'error': 'years_of_experience must be a number'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            if hasattr(user, field):
                setattr(user, field, value)

        user.save()
        return Response(self._serialize_user(request, user))

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Get current user's profile information",
        responses={200: openapi.Response(description="User profile data")}
    )
    def me(self, request):
        """Get current user's profile"""
        user = request.user
        if request.method in ['PUT', 'PATCH']:
            return self._update_profile(request)
        return Response(self._serialize_user(request, user))

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Update current user's profile information",
        responses={200: openapi.Response(description="Profile updated successfully")}
    )
    def update(self, request):
        """Update current user's profile"""
        return self._update_profile(request)

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Upload profile picture",
        responses={200: openapi.Response(description="Profile picture uploaded successfully")}
    )
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_picture(self, request):
        """Upload profile picture"""
        if 'profile_picture' not in request.FILES:
            return Response({'error': 'No file provided'}, status=400)
        
        file = request.FILES['profile_picture']
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in allowed_types:
            return Response({'error': 'Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed.'}, status=400)
        
        user = request.user
        if not hasattr(user, 'profile_picture'):
            return Response({'error': 'Profile picture field is not configured for this user model.'}, status=400)
        user.profile_picture = file
        user.save()
        
        return Response({
            'message': 'Profile picture uploaded successfully',
            'profile_picture_url': self._get_profile_picture_url(request, user),
            'profile_picture': self._get_profile_picture_url(request, user),
            'initials': user.initials
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
        if not hasattr(user, 'profile_picture'):
            return Response({'error': 'Profile picture field is not configured for this user model.'}, status=400)
        if user.profile_picture:
            user.profile_picture.delete()
            user.profile_picture = None
            user.save()
        
        return Response({
            'message': 'Profile picture removed successfully',
            'profile_picture_url': None,
            'initials': user.initials
        })

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Update privacy settings",
        methods=['put', 'patch'],
        responses={200: openapi.Response(description="Privacy settings updated successfully")}
    )
    @action(detail=False, methods=['put', 'patch'])
    def privacy_settings(self, request):
        """Update privacy settings - No privacy fields available in current schema"""
        return Response({'message': 'Privacy settings feature not available'})

    @swagger_auto_schema(
        tags=["auth"],
        operation_description="Update notification preferences",
        methods=['put', 'patch'],
        responses={200: openapi.Response(description="Notification preferences updated successfully")}
    )
    @action(detail=False, methods=['get', 'put', 'patch'])
    def notification_preferences(self, request):
        """Get or update forum notification preferences"""
        user = request.user

        if request.method == 'GET':
            return Response({
                'email_notifications_enabled': user.email_notifications_enabled,
                'email_new_posts': user.email_new_posts,
                'email_new_comments': user.email_new_comments,
                'email_post_replies': user.email_post_replies,
                'email_digest_frequency': user.email_digest_frequency,
            })

        # PUT / PATCH
        data = request.data
        notification_fields = [
            'email_notifications_enabled',
            'email_new_posts',
            'email_new_comments',
            'email_post_replies',
            'email_digest_frequency',
        ]
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
        
        # Calculate is_complete based on required fields
        is_complete = len(missing_required) == 0
        
        return Response({
            'is_complete': is_complete,
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
