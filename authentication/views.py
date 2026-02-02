from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid
from .models import OTP
from .services import TokenService
from .serializers import (
    UserProfileSerializer, 
    UserProfileUpdateSerializer, 
    PasswordChangeSerializer,
    ProfilePictureUploadSerializer
)
from .permissions import IsAuthenticated

User = get_user_model()


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        
        # Validate input
        if not email or not password:
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Email and password are required"
                }
            }, status=400)
        
        # Authenticate real user from database using Django's built-in methods
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password"
                }
            }, status=401)
        
        # Check password using Django's built-in method
        if not user.check_password(password):
            return Response({
                "success": False,
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password"
                }
            }, status=401)
        
        # Generate dynamic OTP
        otp_code = OTP.generate_code()
        
        # Generate unique session ID
        session_id = uuid.uuid4()
        
        # Store OTP in database using the existing OTP model
        otp_instance = OTP.objects.create(
            user=user,
            code=otp_code,
            session_id=session_id,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Get user's display name from email
        user_name = user.email.split('@')[0]
        
        return Response({
            "success": True,
            "session_id": str(session_id),
            "email": user.email,
            "user_name": user_name,
            "message": "OTP sent to your email",
            # For development only - remove in production
            "otp_code": otp_code
        })


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        session_id = request.data.get("session_id")
        otp_code = request.data.get("otp")
        remember_me = request.data.get("remember_me", False)
        
        # Validate input
        if not session_id or not otp_code:
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Session ID and OTP are required"
                }
            }, status=400)
        
        # Retrieve OTP from database
        try:
            otp_instance = OTP.objects.get(
                session_id=session_id,
                is_used=False
            )
        except OTP.DoesNotExist:
            return Response({
                "success": False,
                "error": {
                    "code": "INVALID_OTP",
                    "message": "Invalid or expired OTP session"
                }
            }, status=401)
        
        # Check if OTP matches
        if otp_instance.code != otp_code:
            return Response({
                "success": False,
                "error": {
                    "code": "INVALID_OTP",
                    "message": "Invalid OTP code"
                }
            }, status=401)
        
        # Check if OTP is expired using the model's method
        if not otp_instance.is_valid():
            otp_instance.delete()  # Clean up expired OTP
            return Response({
                "success": False,
                "error": {
                    "code": "EXPIRED_OTP",
                    "message": "OTP has expired"
                }
            }, status=401)
        
        # Mark OTP as used and delete it
        otp_instance.is_used = True
        otp_instance.save()
        otp_instance.delete()  # Remove after use for security
        
        # Generate JWT tokens for the user
        tokens = TokenService.generate_tokens(otp_instance.user, remember_me)
        
        return Response({
            "success": True,
            "message": "OTP verified successfully",
            "access": tokens['access_token'],
            "refresh": tokens['refresh_token'],
            "user": tokens['user']
        })


class ProfileView(APIView):
    """
    Get and update user profile
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user's profile"""
        serializer = UserProfileSerializer(request.user)
        return Response({
            "success": True,
            "user": serializer.data
        })
    
    def put(self, request):
        """Update user profile"""
        serializer = UserProfileUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Return updated profile
            profile_serializer = UserProfileSerializer(request.user)
            return Response({
                "success": True,
                "message": "Profile updated successfully",
                "user": profile_serializer.data
            })
        
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ProfilePictureUploadView(APIView):
    """
    Upload profile picture
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Upload profile picture"""
        serializer = ProfilePictureUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            # Delete old profile picture if exists
            if request.user.profile_picture:
                request.user.profile_picture.delete(save=False)
            
            # Save new profile picture
            request.user.profile_picture = serializer.validated_data['profile_picture']
            request.user.save()
            
            # Return updated profile
            profile_serializer = UserProfileSerializer(request.user)
            return Response({
                "success": True,
                "message": "Profile picture updated successfully",
                "user": profile_serializer.data
            })
        
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Delete profile picture"""
        if request.user.profile_picture:
            request.user.profile_picture.delete(save=True)
            
            # Return updated profile
            profile_serializer = UserProfileSerializer(request.user)
            return Response({
                "success": True,
                "message": "Profile picture deleted successfully",
                "user": profile_serializer.data
            })
        
        return Response({
            "success": False,
            "message": "No profile picture to delete"
        }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    Change user password
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Change password"""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Update password
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            
            return Response({
                "success": True,
                "message": "Password changed successfully"
            })
        
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)