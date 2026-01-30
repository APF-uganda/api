from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid
from .models import OTP
from .services import TokenService

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