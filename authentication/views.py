from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from datetime import datetime
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .services import (
    AuthenticationService,
    OTPService,
    TokenService,
    PasswordResetService,
    AuditLoggingService,
    RateLimitService
)
from .decorators import rate_limit
from .models import AuthLog, AuthEventType

User = get_user_model()


class LoginView(APIView):
    """
    POST /api/v1/auth/login
    Verify email and password, generate OTP
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Authenticate user with email and password, then generate and send OTP",
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
                description="OTP generated successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "OTP sent to your email",
                        "session_id": "uuid-string",
                        "email": "user@example.com",
                        "user_name": "user",
                        "otp_code": "123456"
                    }
                }
            ),
            400: "Bad Request - Missing email or password",
            401: "Unauthorized - Invalid credentials"
        },
        tags=['Authentication']
    )
    @rate_limit
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        # Validate input
        if not email or not password:
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Email and password are required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get client info
        ip_address = AuthenticationService.get_client_ip(request)
        user_agent = AuthenticationService.get_user_agent(request)
        
        # Verify credentials
        user = AuthenticationService.verify_credentials(email, password)
        
        if not user:
            # Log failed attempt
            AuditLoggingService.log_login_attempt(
                user=None,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False
            )
            
            # Track failed attempt for rate limiting
            RateLimitService.track_failed_attempt(ip_address, email)
            
            return Response({
                'success': False,
                'error': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Invalid email or password'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate OTP
        otp, session_id = OTPService.generate_otp(user)
        
        # Log successful login attempt
        AuditLoggingService.log_login_attempt(
            user=user,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        
        # Log OTP generation
        AuditLoggingService.log_otp_generated(
            user=user,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Reset rate limit counters on successful login
        RateLimitService.reset_counters(ip_address, email)
        
        # Prepare response
        response_data = {
            'success': True,
            'message': 'OTP sent to your email',
            'session_id': str(session_id),
            'email': user.email,
            'user_name': user.email.split('@')[0],
            'otp_code': otp.code  # Always include for EmailJS (frontend sends email)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)



class VerifyOTPView(APIView):
    """
    POST /api/v1/auth/verify-otp
    Verify OTP and issue JWT tokens
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Verify OTP code and receive JWT access and refresh tokens",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['session_id', 'otp'],
            properties={
                'session_id': openapi.Schema(type=openapi.TYPE_STRING, description='Session ID from login response'),
                'otp': openapi.Schema(type=openapi.TYPE_STRING, description='6-digit OTP code'),
                'remember_me': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Extend refresh token lifetime', default=False),
            },
        ),
        responses={
            200: openapi.Response(
                description="OTP verified successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "access_token": "jwt-access-token",
                        "refresh_token": "jwt-refresh-token",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "role": "2"
                        }
                    }
                }
            ),
            400: "Bad Request - Missing session_id or OTP",
            401: "Unauthorized - Invalid or expired OTP"
        },
        tags=['Authentication']
    )
    def post(self, request):
        session_id = request.data.get('session_id')
        otp = request.data.get('otp')
        remember_me = request.data.get('remember_me', False)
        
        # Validate input
        if not session_id or not otp:
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Session ID and OTP are required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get client info
        ip_address = AuthenticationService.get_client_ip(request)
        user_agent = AuthenticationService.get_user_agent(request)
        
        # Verify OTP
        user = OTPService.verify_otp(session_id, otp)
        
        if not user:
            # Log failed OTP verification
            AuditLoggingService.log_otp_verification(
                user=None,
                email='unknown',
                ip_address=ip_address,
                user_agent=user_agent,
                success=False
            )
            
            return Response({
                'success': False,
                'error': {
                    'code': 'INVALID_OTP',
                    'message': 'Invalid or expired OTP'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate JWT tokens
        tokens = TokenService.generate_tokens(user, remember_me)
        
        # Log successful OTP verification
        AuditLoggingService.log_otp_verification(
            user=user,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        
        return Response({
            'success': True,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
        }, status=status.HTTP_200_OK)



class RefreshTokenView(APIView):
    """
    POST /api/v1/auth/refresh
    Refresh access token using refresh token
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Refresh JWT access token using a valid refresh token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh_token'],
            properties={
                'refresh_token': openapi.Schema(type=openapi.TYPE_STRING, description='JWT refresh token'),
            },
        ),
        responses={
            200: openapi.Response(
                description="Token refreshed successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "access_token": "new-jwt-access-token",
                        "refresh_token": "new-jwt-refresh-token"
                    }
                }
            ),
            400: "Bad Request - Missing refresh token",
            401: "Unauthorized - Invalid or expired refresh token"
        },
        tags=['Authentication']
    )
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        
        # Validate input
        if not refresh_token:
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Refresh token is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get client info
        ip_address = AuthenticationService.get_client_ip(request)
        user_agent = AuthenticationService.get_user_agent(request)
        
        # Refresh access token
        new_tokens = TokenService.refresh_access_token(refresh_token)
        
        if not new_tokens:
            return Response({
                'success': False,
                'error': {
                    'code': 'INVALID_TOKEN',
                    'message': 'Invalid or expired refresh token'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Log token refresh
        AuditLoggingService.log_auth_event(
            user=None,
            email='token_refresh',
            event_type=AuthEventType.TOKEN_REFRESHED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        
        return Response({
            'success': True,
            'access_token': new_tokens['access_token'],
            'refresh_token': new_tokens.get('refresh_token', refresh_token)
        }, status=status.HTTP_200_OK)



class LogoutView(APIView):
    """
    POST /api/v1/auth/logout
    Invalidate refresh token
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Logout user by blacklisting the refresh token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh_token'],
            properties={
                'refresh_token': openapi.Schema(type=openapi.TYPE_STRING, description='JWT refresh token to blacklist'),
            },
        ),
        responses={
            200: openapi.Response(
                description="Logged out successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Logged out successfully"
                    }
                }
            ),
            400: "Bad Request - Missing refresh token",
            401: "Unauthorized - Invalid or missing access token"
        },
        tags=['Authentication'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        
        # Validate input
        if not refresh_token:
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Refresh token is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get client info
        ip_address = AuthenticationService.get_client_ip(request)
        user_agent = AuthenticationService.get_user_agent(request)
        
        # Invalidate refresh token (blacklist it)
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            # Token might already be blacklisted or invalid
            pass
        
        # Log logout
        AuditLoggingService.log_auth_event(
            user=request.user,
            email=request.user.email,
            event_type=AuthEventType.LOGOUT,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)



class CurrentUserView(APIView):
    """
    GET /api/v1/auth/me
    Get current authenticated user information
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get current authenticated user's profile information",
        responses={
            200: openapi.Response(
                description="User information retrieved successfully",
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@example.com",
                        "role": "2",
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                }
            ),
            401: "Unauthorized - Invalid or missing access token"
        },
        tags=['Authentication'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        user = request.user
        
        return Response({
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'created_at': user.created_at.isoformat()
        }, status=status.HTTP_200_OK)



class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset-request
    Request password reset token
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Request a password reset token to be sent to the user's email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email address'),
            },
        ),
        responses={
            200: openapi.Response(
                description="Password reset request processed",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Password reset instructions sent to your email"
                    }
                }
            ),
            400: "Bad Request - Missing email"
        },
        tags=['Authentication']
    )
    def post(self, request):
        email = request.data.get('email')
        
        # Validate input
        if not email:
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Email is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get client info
        ip_address = AuthenticationService.get_client_ip(request)
        user_agent = AuthenticationService.get_user_agent(request)
        
        # Request password reset (always returns success for security)
        PasswordResetService.request_password_reset(email)
        
        # Log password reset request
        AuditLoggingService.log_password_reset_request(
            user=None,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Always return success even if email doesn't exist (security best practice)
        return Response({
            'success': True,
            'message': 'Password reset instructions sent to your email'
        }, status=status.HTTP_200_OK)



class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password-reset-confirm
    Complete password reset with token
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Complete password reset using the token received via email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['token', 'new_password'],
            properties={
                'token': openapi.Schema(type=openapi.TYPE_STRING, description='Password reset token from email'),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='New password (min 8 characters)'),
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
            400: "Bad Request - Missing token/password or password too short",
            401: "Unauthorized - Invalid or expired reset token"
        },
        tags=['Authentication']
    )
    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        # Validate input
        if not token or not new_password:
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Token and new password are required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength (minimum 8 characters)
        if len(new_password) < 8:
            return Response({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Password must be at least 8 characters long'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get client info
        ip_address = AuthenticationService.get_client_ip(request)
        user_agent = AuthenticationService.get_user_agent(request)
        
        # Confirm password reset
        user = PasswordResetService.confirm_password_reset(token, new_password)
        
        if not user:
            return Response({
                'success': False,
                'error': {
                    'code': 'INVALID_RESET_TOKEN',
                    'message': 'Invalid or expired password reset token'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Invalidate all user refresh tokens
        PasswordResetService.invalidate_user_tokens(user)
        
        # Log password reset completion
        AuditLoggingService.log_password_reset_completed(
            user=user,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return Response({
            'success': True,
            'message': 'Password reset successfully'
        }, status=status.HTTP_200_OK)



class AuthLogsView(APIView):
    """
    GET /api/v1/auth/logs
    Retrieve authentication logs (admin only)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Retrieve authentication logs with filtering and pagination (Admin only)",
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, description="Filter by email", type=openapi.TYPE_STRING),
            openapi.Parameter('event_type', openapi.IN_QUERY, description="Filter by event type", type=openapi.TYPE_STRING),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Filter by start date (ISO format)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="Filter by end date (ISO format)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page", type=openapi.TYPE_INTEGER, default=20),
        ],
        responses={
            200: openapi.Response(
                description="Authentication logs retrieved successfully",
                examples={
                    "application/json": {
                        "count": 100,
                        "next": "/api/v1/auth/logs?page=2",
                        "previous": None,
                        "results": [
                            {
                                "id": 1,
                                "email": "user@example.com",
                                "event_type": "LOGIN_ATTEMPT",
                                "ip_address": "192.168.1.1",
                                "timestamp": "2024-01-01T00:00:00Z",
                                "success": True,
                                "details": {}
                            }
                        ]
                    }
                }
            ),
            401: "Unauthorized - Invalid or missing access token",
            403: "Forbidden - Admin access required"
        },
        tags=['Authentication'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        # Check if user is admin
        if request.user.role != '1':
            return Response({
                'success': False,
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Admin access required'
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get query parameters
        email = request.query_params.get('email')
        event_type = request.query_params.get('event_type')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Build query
        queryset = AuthLog.objects.all()
        
        if email:
            queryset = queryset.filter(email__icontains=email)
        
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__lte=end_dt)
            except ValueError:
                pass
        
        # Paginate results
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # Serialize results
        results = []
        for log in page_obj:
            results.append({
                'id': log.id,
                'email': log.email,
                'event_type': log.event_type,
                'ip_address': log.ip_address,
                'timestamp': log.timestamp.isoformat(),
                'success': log.success,
                'details': log.details
            })
        
        # Build pagination URLs
        next_url = None
        previous_url = None
        
        if page_obj.has_next():
            next_url = f'/api/auth/logs?page={page_obj.next_page_number()}'
            if email:
                next_url += f'&email={email}'
            if event_type:
                next_url += f'&event_type={event_type}'
        
        if page_obj.has_previous():
            previous_url = f'/api/auth/logs?page={page_obj.previous_page_number()}'
            if email:
                previous_url += f'&email={email}'
            if event_type:
                previous_url += f'&event_type={event_type}'
        
        return Response({
            'count': paginator.count,
            'next': next_url,
            'previous': previous_url,
            'results': results
        }, status=status.HTTP_200_OK)
