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
from .services import TokenService, EmailService
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
    
    # Test users that bypass OTP verification
    OTP_BYPASS_USERS = ['admin@apt.com', 'member@apf.com']
    
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        remember_me = request.data.get("remember_me", False)
        
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
        
        # Check if user should bypass OTP
        if email in self.OTP_BYPASS_USERS:
            # Generate JWT tokens directly without OTP
            tokens = TokenService.generate_tokens(user, remember_me)
            
            return Response({
                "success": True,
                "message": "Login successful (OTP bypassed for test user)",
                "access": tokens['access_token'],
                "refresh": tokens['refresh_token'],
                "user": tokens['user'],
                "otp_bypassed": True
            })
        
        # Generate dynamic OTP for regular users
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
        
        # Send OTP email via EmailJS
        EmailService.send_otp_email(
            email=user.email,
            otp_code=otp_code,
            user_name=user_name
        )
        
        return Response({
            "success": True,
            "session_id": str(session_id),
            "email": user.email,
            "user_name": user_name,
            "message": "OTP sent to your email"
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


class ForgotPasswordView(APIView):
    """
    Request password reset OTP
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get("email")
        
        # Validate input
        if not email:
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Email is required"
                }
            }, status=400)
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Return success even if user doesn't exist (security best practice)
            return Response({
                "success": True,
                "message": "If the email exists, an OTP has been sent"
            })
        
        # Generate OTP
        otp_code = OTP.generate_code()
        
        # Generate unique session ID
        session_id = uuid.uuid4()
        
        # Store OTP in database
        OTP.objects.create(
            user=user,
            code=otp_code,
            session_id=session_id,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Get user's display name
        user_name = user.email.split('@')[0]
        
        # Send password reset OTP email via EmailJS
        EmailService.send_password_reset_email(
            email=user.email,
            otp_code=otp_code,
            user_name=user_name
        )
        
        return Response({
            "success": True,
            "session_id": str(session_id),
            "email": user.email,
            "user_name": user_name,
            "message": "OTP sent to your email"
        })


class ResetPasswordView(APIView):
    """
    Reset password using OTP
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        session_id = request.data.get("session_id")
        otp_code = request.data.get("otp")
        new_password = request.data.get("new_password")
        
        # Validate input
        if not session_id or not otp_code or not new_password:
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Session ID, OTP, and new password are required"
                }
            }, status=400)
        
        # Validate password strength
        if len(new_password) < 8:
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Password must be at least 8 characters long"
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
        
        # Check if OTP is expired
        if not otp_instance.is_valid():
            otp_instance.delete()
            return Response({
                "success": False,
                "error": {
                    "code": "EXPIRED_OTP",
                    "message": "OTP has expired"
                }
            }, status=401)
        
        # Update user password
        user = otp_instance.user
        user.set_password(new_password)
        user.save()
        
        # Mark OTP as used and delete it
        otp_instance.is_used = True
        otp_instance.save()
        otp_instance.delete()
        
        return Response({
            "success": True,
            "message": "Password reset successfully"
        })


class ResendLoginOTPView(APIView):
    """
    Resend OTP for login without requiring password again
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        session_id = request.data.get("session_id")
        
        # Validate input
        if not session_id:
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Session ID is required"
                }
            }, status=400)
        
        # Find the existing OTP session
        try:
            old_otp = OTP.objects.get(session_id=session_id, is_used=False)
            user = old_otp.user
            
            # Delete old OTP
            old_otp.delete()
            
            # Generate new OTP
            otp_code = OTP.generate_code()
            
            # Create new OTP with same session_id
            OTP.objects.create(
                user=user,
                code=otp_code,
                session_id=session_id,
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # Get user's display name
            user_name = user.email.split('@')[0]
            
            # Send OTP email via EmailJS
            EmailService.send_otp_email(
                email=user.email,
                otp_code=otp_code,
                user_name=user_name
            )
            
            return Response({
                "success": True,
                "message": "New OTP sent to your email",
                "email": user.email
            })
            
        except OTP.DoesNotExist:
            return Response({
                "success": False,
                "error": {
                    "code": "INVALID_SESSION",
                    "message": "Invalid or expired session"
                }
            }, status=404)


class ResendPasswordResetOTPView(APIView):
    """
    Resend OTP for password reset
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        session_id = request.data.get("session_id")
        
        # Validate input
        if not session_id:
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Session ID is required"
                }
            }, status=400)
        
        # Find the existing OTP session
        try:
            old_otp = OTP.objects.get(session_id=session_id, is_used=False)
            user = old_otp.user
            
            # Delete old OTP
            old_otp.delete()
            
            # Generate new OTP
            otp_code = OTP.generate_code()
            
            # Create new OTP with same session_id
            OTP.objects.create(
                user=user,
                code=otp_code,
                session_id=session_id,
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # Get user's display name
            user_name = user.email.split('@')[0]
            
            # Send password reset OTP email via EmailJS
            EmailService.send_password_reset_email(
                email=user.email,
                otp_code=otp_code,
                user_name=user_name
            )
            
            return Response({
                "success": True,
                "message": "New OTP sent to your email",
                "email": user.email
            })
            
        except OTP.DoesNotExist:
            return Response({
                "success": False,
                "error": {
                    "code": "INVALID_SESSION",
                    "message": "Invalid or expired session"
                }
            }, status=404)
