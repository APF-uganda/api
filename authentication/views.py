import re
import uuid
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import OTP
from .services import TokenService, UserCreationService
from .email_service_smtp import EmailService
from .serializers import PasswordChangeSerializer
from .permissions import IsAuthenticated

User = get_user_model()
logger = logging.getLogger(__name__)


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    # Test users that bypass OTP verification
    OTP_BYPASS_USERS = ['admin@apt.com', 'member@apf.com']
    
    @swagger_auto_schema(
        operation_description="Login with email and password. Sends OTP to email for verification.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email address'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='User password'),
            },
        ),
        responses={
            200: openapi.Response(
                description="OTP sent successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "session_id": "uuid-string",
                        "email": "user@example.com",
                        "user_name": "user",
                        "message": "OTP sent to your email"
                    }
                }
            ),
            400: "Validation error",
            401: "Invalid credentials"
        },
        tags=['Authentication']
    )
    def post(self, request):
        email = (request.data.get("email") or "").strip()
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
        user = User.objects.filter(email__iexact=email).first()

        # Recovery path: if this approved application has no linked user yet,
        # create/reactivate the account on-demand during login.
        if not user:
            try:
                from applications.models import Application

                approved_application = (
                    Application.objects
                    .filter(email__iexact=email, status='approved')
                    .order_by('-updated_at', '-submitted_at')
                    .first()
                )

                if approved_application:
                    recovered_user, recovery_error = UserCreationService.create_user_from_application(
                        approved_application
                    )
                    if recovered_user:
                        user = recovered_user
                    else:
                        logger.warning(
                            "Failed to recover login user from approved application for %s: %s",
                            email,
                            recovery_error,
                        )
            except Exception:
                logger.exception("Error while recovering login user from approved application for %s", email)

        if not user:
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
        if user.email.lower() in {bypass_email.lower() for bypass_email in self.OTP_BYPASS_USERS}:
            # Generate JWT tokens directly without OTP
            tokens = TokenService.generate_tokens(user)
            
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
        
        # Get user's first name or fallback to email username
        user_name = user.first_name if user.first_name else user.email.split('@')[0]
        
        # Send OTP email via SMTP
        email_sent = EmailService.send_otp_email(
            email=user.email,
            otp_code=otp_code,
            user_name=user_name
        )
        
        if not email_sent:
            # Clean up the OTP since email failed
            otp_instance.delete()
            return Response({
                "success": False,
                "error": {
                    "code": "EMAIL_SEND_FAILED",
                    "message": "Failed to send OTP email. Please check server email configuration."
                }
            }, status=500)
        
        return Response({
            "success": True,
            "session_id": str(session_id),
            "email": user.email,
            "user_name": user_name,
            "message": "OTP sent to your email"
        })


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Verify OTP code and receive JWT tokens",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['session_id', 'otp'],
            properties={
                'session_id': openapi.Schema(type=openapi.TYPE_STRING, description='Session ID from login response'),
                'otp': openapi.Schema(type=openapi.TYPE_STRING, description='6-digit OTP code from email'),
            },
        ),
        responses={
            200: openapi.Response(
                description="OTP verified successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Login successful",
                        "access": "jwt-access-token",
                        "refresh": "jwt-refresh-token",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "role": "2"
                        }
                    }
                }
            ),
            400: "Validation error or invalid OTP",
            404: "Session not found"
        },
        tags=['Authentication']
    )
    def post(self, request):
        session_id = request.data.get("session_id")
        otp_code = request.data.get("otp")
        
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
        user = otp_instance.user
        otp_instance.is_used = True
        otp_instance.save()
        otp_instance.delete()  # Remove after use for security
        
        # Generate JWT tokens for the user
        tokens = TokenService.generate_tokens(user)
        
        return Response({
            "success": True,
            "message": "OTP verified successfully",
            "access": tokens['access_token'],
            "refresh": tokens['refresh_token'],
            "user": tokens['user']
        })


class ChangePasswordView(APIView):
    """
    Change user password
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Change user password (requires authentication)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['current_password', 'new_password', 'confirm_password'],
            properties={
                'current_password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='password',
                    description='Current password'
                ),
                'new_password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='password',
                    description='New password (min 8 characters)'
                ),
                'confirm_password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='password',
                    description='Confirm new password'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Password changed successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Password changed successfully"
                    }
                }
            ),
            400: "Validation error",
            401: "Unauthorized"
        },
        tags=['Authentication'],
        security=[{'Bearer': []}]
    )
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
    
    @swagger_auto_schema(
        operation_description="Request password reset OTP - Sends OTP to email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='email',
                    description='Email address of the account',
                    example='user@example.com'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="OTP sent (or email not found - security)",
                examples={
                    "application/json": {
                        "success": True,
                        "session_id": "uuid-string",
                        "message": "Password reset OTP sent to your email"
                    }
                }
            ),
            400: "Validation error"
        },
        tags=['Authentication']
    )
    def post(self, request):
        email = (request.data.get("email") or "").strip()
        
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
        user = User.objects.filter(email__iexact=email).first()

        # Recovery path: for approved applications that don't yet have a user account,
        # create/reactivate the account so password reset can proceed.
        if not user:
            try:
                from applications.models import Application

                approved_application = (
                    Application.objects
                    .filter(email__iexact=email, status='approved')
                    .order_by('-updated_at', '-submitted_at')
                    .first()
                )

                if approved_application:
                    recovered_user, recovery_error = UserCreationService.create_user_from_application(
                        approved_application
                    )
                    if recovered_user:
                        user = recovered_user
                    else:
                        logger.warning(
                            "Failed to recover user from approved application for %s: %s",
                            email,
                            recovery_error,
                        )
            except Exception:
                logger.exception("Error while recovering user from approved application for %s", email)

        if not user:
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
        otp_instance = OTP.objects.create(
            user=user,
            code=otp_code,
            session_id=session_id,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Get user's first name or fallback to email username
        user_name = user.first_name if user.first_name else user.email.split('@')[0]
        
        # Send password reset OTP email via SMTP
        email_sent = EmailService.send_password_reset_email(
            email=user.email,
            otp_code=otp_code,
            user_name=user_name
        )
        
        if not email_sent:
            otp_instance.delete()
            return Response({
                "success": False,
                "error": {
                    "code": "EMAIL_SEND_FAILED",
                    "message": "Failed to send OTP email. Please check server email configuration."
                }
            }, status=500)
        
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
    
    @swagger_auto_schema(
        operation_description="Reset password using OTP code from email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['session_id', 'otp', 'new_password'],
            properties={
                'session_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Session ID from forgot password response'
                ),
                'otp': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='6-digit OTP code from email'
                ),
                'new_password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='password',
                    description='New password (min 8 characters)'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Password reset successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Password reset successfully"
                    }
                }
            ),
            400: "Validation error or invalid OTP",
            404: "Session not found"
        },
        tags=['Authentication']
    )
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
        if not re.search(r'[A-Za-z]', new_password):
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Password must contain at least one letter"
                }
            }, status=400)
        if not re.search(r'\d', new_password):
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Password must contain at least one number"
                }
            }, status=400)
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/~`]', new_password):
            return Response({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Password must contain at least one special character"
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
    
    @swagger_auto_schema(
        operation_description="Resend OTP for login using existing session ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['session_id'],
            properties={
                'session_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Session ID from original login request'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="New OTP sent successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "New OTP sent to your email",
                        "email": "user@example.com"
                    }
                }
            ),
            400: "Validation error - session_id required",
            404: "Invalid or expired session"
        },
        tags=['Authentication']
    )
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
            new_otp = OTP.objects.create(
                user=user,
                code=otp_code,
                session_id=session_id,
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # Get user's display name
            user_name = user.email.split('@')[0]
            
            # Send OTP email via SMTP
            email_sent = EmailService.send_otp_email(
                email=user.email,
                otp_code=otp_code,
                user_name=user_name
            )
            
            if not email_sent:
                new_otp.delete()
                return Response({
                    "success": False,
                    "error": {
                        "code": "EMAIL_SEND_FAILED",
                        "message": "Failed to send OTP email. Please check server email configuration."
                    }
                }, status=500)
            
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
    
    @swagger_auto_schema(
        operation_description="Resend OTP for password reset using existing session ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['session_id'],
            properties={
                'session_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Session ID from forgot password request'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="New OTP sent successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "New OTP sent to your email",
                        "email": "user@example.com"
                    }
                }
            ),
            400: "Validation error - session_id required",
            404: "Invalid or expired session"
        },
        tags=['Authentication']
    )
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
            new_otp = OTP.objects.create(
                user=user,
                code=otp_code,
                session_id=session_id,
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # Get user's first name or fallback to email username
            user_name = user.first_name if user.first_name else user.email.split('@')[0]
            
            # Send password reset OTP email via SMTP
            email_sent = EmailService.send_password_reset_email(
                email=user.email,
                otp_code=otp_code,
                user_name=user_name
            )
            
            if not email_sent:
                new_otp.delete()
                return Response({
                    "success": False,
                    "error": {
                        "code": "EMAIL_SEND_FAILED",
                        "message": "Failed to send OTP email. Please check server email configuration."
                    }
                }, status=500)
            
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
