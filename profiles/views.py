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
            # Log what we're returning
            print(f"[Profile GET] User: {request.user.email}")
            print(f"[Profile GET] Profile data: first_name={profile.first_name}, last_name={profile.last_name}, phone={profile.phone_number}")
            
            serializer = UserProfileSerializer(profile, context={'request': request})
            return Response(serializer.data)
        
        # Handle updates - use update serializer
        print(f"[Profile UPDATE] User: {request.user.email}")
        print(f"[Profile UPDATE] Request data: {request.data}")
        print(f"[Profile UPDATE] Current profile: first_name={profile.first_name}, last_name={profile.last_name}")
        
        update_serializer = UserProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        
        if update_serializer.is_valid():
            try:
                # Save profile (with transaction)
                with transaction.atomic():
                    # Track changes for logging
                    changed_fields = []
                    original_values = {}
                    if hasattr(update_serializer, 'validated_data'):
                        changed_fields = list(update_serializer.validated_data.keys())
                        for field in changed_fields:
                            original_values[field] = getattr(profile, field, None)
                    
                    print(f"[Profile UPDATE] Validated data: {update_serializer.validated_data}")
                    
                    # Save profile
                    updated_profile = update_serializer.save()
                    
                    print(f"[Profile UPDATE] After save: first_name={updated_profile.first_name}, last_name={updated_profile.last_name}")
                    
                    # Refresh from database to ensure all relations are loaded
                    updated_profile.refresh_from_db()
                    
                    print(f"[Profile UPDATE] After refresh: first_name={updated_profile.first_name}, last_name={updated_profile.last_name}")
                    
                    # Verify data is actually in database
                    db_check = UserProfile.objects.get(user=request.user)
                    print(f"[Profile UPDATE] Database check (inside transaction): first_name={db_check.first_name}, last_name={db_check.last_name}")
                
                # Transaction committed! Check database again
                final_check = UserProfile.objects.get(user=request.user)
                print(f"[Profile UPDATE] Database check (AFTER transaction): first_name={final_check.first_name}, last_name={final_check.last_name}")
                
                # Log activity OUTSIDE the transaction (so it doesn't cause rollback)
                try:
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
                        field_changed=', '.join(changed_fields) if changed_fields else 'profile',
                        metadata={'changes': changes} if changes else {},
                        request=request
                    )
                except Exception as log_error:
                    # Don't fail the update if logging fails
                    print(f"Warning: Failed to log profile activity: {log_error}")
                
                # Return full profile data using the read serializer
                response_serializer = UserProfileSerializer(updated_profile, context={'request': request})
                print(f"[Profile UPDATE] Returning: {response_serializer.data.get('first_name')}, {response_serializer.data.get('last_name')}")
                
                return Response(response_serializer.data)
            except Exception as e:
                # Log the error for debugging
                print(f"Error updating profile: {str(e)}")
                import traceback
                traceback.print_exc()
                return Response(
                    {'error': f'Failed to update profile: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        print(f"[Profile UPDATE] Validation errors: {update_serializer.errors}")
        return Response(update_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_picture(self, request):
        """
        Upload or update profile picture.
        """
        print(f"[Profile UPLOAD] User: {request.user.email}")
        print(f"[Profile UPLOAD] Files: {request.FILES}")
        
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        serializer = self.get_serializer(profile, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Remove old picture if exists
                    if profile.profile_picture:
                        ProfileService.remove_profile_picture(profile)
                    
                    # Save new picture
                    updated_profile = serializer.save()
                    print(f"[Profile UPLOAD] Picture saved: {updated_profile.profile_picture}")
                    print(f"[Profile UPLOAD] Picture name: {updated_profile.profile_picture.name if updated_profile.profile_picture else 'None'}")
                    print(f"[Profile UPLOAD] Has url attr: {hasattr(updated_profile.profile_picture, 'url') if updated_profile.profile_picture else False}")
                
                # Refresh from database
                updated_profile.refresh_from_db()
                print(f"[Profile UPLOAD] After refresh - Picture: {updated_profile.profile_picture}")
                
                # Log activity
                file_name = os.path.basename(updated_profile.profile_picture.name) if updated_profile.profile_picture else ''
                ProfileService.log_activity(
                    profile=updated_profile,
                    action='picture_uploaded',
                    metadata={'document_name': file_name} if file_name else {},
                    request=request
                )
                # Log activity OUTSIDE transaction
                try:
                    ProfileService.log_activity(
                        profile=updated_profile,
                        action='picture_uploaded',
                        request=request
                    )
                except Exception as log_error:
                    print(f"Warning: Failed to log picture upload: {log_error}")
                
                picture_url = updated_profile.get_profile_picture_url()
                print(f"[Profile UPLOAD] Picture URL: {picture_url}")
                
                return Response({
                    'message': 'Profile picture uploaded successfully',
                    'profile_picture_url': request.build_absolute_uri(picture_url) if picture_url else None,
                    'initials': updated_profile.get_initials()
                })
            except Exception as e:
                print(f"Error uploading picture: {str(e)}")
                import traceback
                traceback.print_exc()
                return Response(
                    {'error': f'Failed to upload picture: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        print(f"[Profile UPLOAD] Validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def remove_picture(self, request):
        """
        Remove profile picture.
        """
        print(f"[Profile REMOVE] User: {request.user.email}")
        
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
        
        previous_picture = profile.profile_picture.name if profile.profile_picture else ''
        try:
            with transaction.atomic():
                # Remove picture file and clear field
                ProfileService.remove_profile_picture(profile)
                profile.profile_picture = None
                profile.save()
                print(f"[Profile REMOVE] Picture removed successfully")
            
            # Log activity OUTSIDE transaction
            try:
                ProfileService.log_activity(
                    profile=profile,
                    action='picture_removed',
                    metadata={'document_name': os.path.basename(previous_picture)} if previous_picture else {},
                    request=request
                )
            except Exception as log_error:
                print(f"Warning: Failed to log picture removal: {log_error}")
            
            return Response({
                'message': 'Profile picture removed successfully',
                'initials': profile.get_initials()
            })
        except Exception as e:
            print(f"Error removing picture: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to remove picture: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
