"""
Profile views for API endpoints.
Follows SOLID principles with proper separation of concerns.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import os

from .models import UserProfile, ProfileActivityLog
from .serializers import (
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    ProfilePictureSerializer,
    PrivacySettingsSerializer,
    NotificationPreferencesSerializer,
    ProfileSummarySerializer,
    ProfileActivityLogSerializer
)
from .services import ProfileService
from authentication.permissions import IsAuthenticated, IsOwnerOrAdmin


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user profile management.
    
    Endpoints:
    - GET /api/v1/profiles/ - List profiles (admin only)
    - GET /api/v1/profiles/me/ - Get current user's profile
    - PUT/PATCH /api/v1/profiles/me/ - Update current user's profile
    - POST /api/v1/profiles/upload-picture/ - Upload profile picture
    - DELETE /api/v1/profiles/remove-picture/ - Remove profile picture
    - PUT /api/v1/profiles/privacy-settings/ - Update privacy settings
    - PUT /api/v1/profiles/notification-preferences/ - Update notification preferences
    """
    
    serializer_class = UserProfileSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Return profiles based on user permissions."""
        user = self.request.user
        
        if user.role == '1':  # Admin
            return UserProfile.objects.all().select_related('user')
        else:
            # Regular users can only see their own profile
            return UserProfile.objects.filter(user=user).select_related('user')
    
    def get_object(self):
        """Get profile object with proper permissions."""
        if self.action == 'me':
            profile, created = UserProfile.objects.get_or_create(user=self.request.user)
            if created:
                ProfileService.log_activity(
                    profile=profile,
                    action='created',
                    metadata={'created': True},
                    request=self.request
                )
            return profile
        
        return super().get_object()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'upload_picture':
            return ProfilePictureSerializer
        elif self.action == 'privacy_settings':
            return PrivacySettingsSerializer
        elif self.action == 'notification_preferences':
            return NotificationPreferencesSerializer
        elif self.action == 'list':
            return ProfileSummarySerializer
        elif self.action in ['update', 'partial_update']:
            return UserProfileUpdateSerializer
        
        return UserProfileSerializer
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """
        Get or update current user's profile.
        """
        profile = self.get_object()
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile, context={'request': request})
            return Response(serializer.data)
        
        # Handle updates
        serializer = self.get_serializer(
            profile,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                # Track changes for logging
                changed_fields = []
                original_values = {}
                if hasattr(serializer, 'validated_data'):
                    changed_fields = list(serializer.validated_data.keys())
                    for field in changed_fields:
                        original_values[field] = getattr(profile, field, None)
                
                # Save profile
                updated_profile = serializer.save()
                
                # Log activity
                changes = []
                for field in changed_fields:
                    changes.append({
                        'field': field,
                        'old': original_values.get(field),
                        'new': getattr(updated_profile, field, None),
                    })
                ProfileService.log_activity(
                    profile=updated_profile,
                    action='updated',
                    field_changed=', '.join(changed_fields),
                    metadata={'changes': changes} if changes else {},
                    request=request
                )
            
            # Return full profile data
            response_serializer = UserProfileSerializer(updated_profile, context={'request': request})
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_picture(self, request):
        """
        Upload or update profile picture.
        """
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        serializer = self.get_serializer(profile, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            with transaction.atomic():
                # Remove old picture if exists
                if profile.profile_picture:
                    ProfileService.remove_profile_picture(profile)
                
                # Save new picture
                updated_profile = serializer.save()
                
                # Log activity
                file_name = os.path.basename(updated_profile.profile_picture.name) if updated_profile.profile_picture else ''
                ProfileService.log_activity(
                    profile=updated_profile,
                    action='picture_uploaded',
                    metadata={'document_name': file_name} if file_name else {},
                    request=request
                )
            
            return Response({
                'message': 'Profile picture uploaded successfully',
                'profile_picture_url': request.build_absolute_uri(updated_profile.get_profile_picture_url()),
                'initials': updated_profile.get_initials()
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def remove_picture(self, request):
        """
        Remove profile picture.
        """
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not profile.profile_picture:
            return Response(
                {'error': 'No profile picture to remove'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            
            previous_picture = profile.profile_picture.name if profile.profile_picture else ''
            ProfileService.remove_profile_picture(profile)
            profile.profile_picture = None
            profile.save()
            
            # Log activity
            ProfileService.log_activity(
                profile=profile,
                action='picture_removed',
                metadata={'document_name': os.path.basename(previous_picture)} if previous_picture else {},
                request=request
            )
        
        return Response({
            'message': 'Profile picture removed successfully',
            'initials': profile.get_initials()
        })
    
    @action(detail=False, methods=['put', 'patch'])
    def privacy_settings(self, request):
        """
        Update privacy settings.
        """
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        serializer = self.get_serializer(
            profile,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                changed_fields = list(serializer.validated_data.keys())
                original_values = {field: getattr(profile, field, None) for field in changed_fields}
                updated_profile = serializer.save()
                
                # Log activity
                changes = []
                for field in changed_fields:
                    changes.append({
                        'field': field,
                        'old': original_values.get(field),
                        'new': getattr(updated_profile, field, None),
                    })
                ProfileService.log_activity(
                    profile=updated_profile,
                    action='privacy_changed',
                    metadata={'changes': changes} if changes else {},
                    request=request
                )
            
            return Response({
                'message': 'Privacy settings updated successfully',
                'settings': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['put', 'patch'])
    def notification_preferences(self, request):
        """
        Update notification preferences.
        """
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        serializer = self.get_serializer(
            profile,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                changed_fields = list(serializer.validated_data.keys())
                original_values = {field: getattr(profile, field, None) for field in changed_fields}
                updated_profile = serializer.save()
                
                # Log activity
                changes = []
                for field in changed_fields:
                    changes.append({
                        'field': field,
                        'old': original_values.get(field),
                        'new': getattr(updated_profile, field, None),
                    })
                ProfileService.log_activity(
                    profile=updated_profile,
                    action='notifications_changed',
                    metadata={'changes': changes} if changes else {},
                    request=request
                )
            
            return Response({
                'message': 'Notification preferences updated successfully',
                'preferences': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def activity_log(self, request):
        """
        Get profile activity log for current user.
        """
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        logs = profile.activity_logs.all()[:20]  # Last 20 activities
        serializer = ProfileActivityLogSerializer(logs, many=True)
        
        return Response({
            'activities': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def completion_status(self, request):
        """
        Get profile completion status and suggestions.
        """
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        completion_data = ProfileService.get_completion_status(profile)
        
        return Response(completion_data)
