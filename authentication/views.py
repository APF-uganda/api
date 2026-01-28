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
    POST /api/auth/login
    Verify email and password, generate OTP
    """
    permission_classes = [AllowAny]
    
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
    POST /api/auth/verify-otp
    Verify OTP and issue JWT tokens
    """
    permission_classes = [AllowAny]
    
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
    POST /api/auth/refresh
    Refresh access token using refresh token
    """
    permission_classes = [AllowAny]
    
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
    POST /api/auth/logout
    Invalidate refresh token
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
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
    GET /api/auth/me
    Get current authenticated user information
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
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
    POST /api/auth/password-reset-request
    Request password reset token
    """
    permission_classes = [AllowAny]
    
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
    POST /api/auth/password-reset-confirm
    Complete password reset with token
    """
    permission_classes = [AllowAny]
    
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
    GET /api/auth/logs
    Retrieve authentication logs (admin only)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
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
