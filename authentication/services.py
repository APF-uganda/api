"""
Authentication services for handling authentication logic
"""

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password, identify_hasher
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from datetime import timedelta
import uuid
import requests
import logging
from authentication.models import User, OTP, PasswordResetToken, AuthLog, AuthEventType, UserRole
from profiles.models import UserProfile
from Documents.models import Document
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Service for handling user authentication"""
    
    @staticmethod
    def verify_credentials(email, password):
        """
        Verify email and password credentials
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            User object if credentials are valid, None otherwise
        """
        try:
            user = User.objects.get(email=email)
            logger.info(f"User found: {email}, is_active: {user.is_active}")
            
            password_valid = user.check_password(password)
            logger.info(f"Password check result for {email}: {password_valid}")
            
            if user.is_active and password_valid:
                logger.info(f"Authentication successful for {email}")
                return user
            else:
                logger.warning(f"Authentication failed for {email} - active: {user.is_active}, password_valid: {password_valid}")
        except User.DoesNotExist:
            logger.warning(f"User not found: {email}")
            # Return None to avoid revealing whether email exists
            pass
        return None
    
    @staticmethod
    def get_client_ip(request):
        """
        Extract client IP address from request
        
        Args:
            request: Django request object
            
        Returns:
            IP address as string
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    @staticmethod
    def get_user_agent(request):
        """
        Extract user agent from request
        
        Args:
            request: Django request object
            
        Returns:
            User agent string
        """
        return request.META.get('HTTP_USER_AGENT', '')


class OTPService:
    """Service for handling OTP generation and verification"""
    
    @staticmethod
    def generate_otp(user):
        """
        Generate and store OTP for user
        
        Args:
            user: User object
            
        Returns:
            Tuple of (OTP object, session_id)
        """
        # Invalidate any previous unexpired OTPs
        OTPService.invalidate_previous_otps(user)
        
        # Generate new OTP
        code = OTP.generate_code()
        session_id = uuid.uuid4()
        expires_at = timezone.now() + timedelta(minutes=10)
        
        otp = OTP.objects.create(
            user=user,
            code=code,
            session_id=session_id,
            expires_at=expires_at
        )
        
        # Send OTP email
        try:
            email_sent = EmailService.send_otp_email(
                email=user.email,
                otp_code=code,
                user_name=user.email.split('@')[0]
            )
            
            if not email_sent:
                logger.warning(f"Failed to send OTP email to {user.email}, but OTP was created")
        except Exception as e:
            logger.error(f"Exception while sending OTP email to {user.email}: {str(e)}")
            # Continue even if email fails - OTP is still valid
        
        return otp, session_id
    
    @staticmethod
    def verify_otp(session_id, code):
        """
        Verify OTP code for given session
        
        Args:
            session_id: UUID session identifier
            code: 6-digit OTP code
            
        Returns:
            User object if OTP is valid, None otherwise
        """
        try:
            otp = OTP.objects.get(session_id=session_id)
            
            if otp.is_valid() and otp.code == code:
                # Mark OTP as used
                otp.is_used = True
                otp.save()
                return otp.user
        except OTP.DoesNotExist:
            pass
        
        return None
    
    @staticmethod
    def invalidate_previous_otps(user):
        """
        Invalidate all previous unexpired OTPs for user
        
        Args:
            user: User object
        """
        OTP.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).update(is_used=True)


class TokenService:
    """Service for handling JWT token generation and refresh"""
    
    @staticmethod
    def generate_tokens(user, remember_me=False):
        """
        Generate JWT access and refresh tokens for user
        
        Args:
            user: User object
            remember_me: Boolean flag for extended refresh token lifetime
            
        Returns:
            Dictionary with access_token, refresh_token, and user info
        """
        refresh = RefreshToken.for_user(user)
        
        # Add custom claims to token payload
        refresh['email'] = user.email
        refresh['role'] = user.role
        
        # Set refresh token expiration based on remember_me
        if remember_me:
            refresh.set_exp(lifetime=timedelta(days=30))
        else:
            refresh.set_exp(lifetime=timedelta(days=1))
        
        return {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
        }
    
    @staticmethod
    def refresh_access_token(refresh_token):
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            Dictionary with new access_token and refresh_token, or None if invalid
        """
        try:
            refresh = RefreshToken(refresh_token)
            
            # Generate new access token
            access_token = str(refresh.access_token)
            
            # Optionally rotate refresh token
            new_refresh_token = str(refresh)
            
            return {
                'access_token': access_token,
                'refresh_token': new_refresh_token
            }
        except Exception:
            return None


class PasswordResetService:
    """Service for handling password reset functionality"""
    
    @staticmethod
    def request_password_reset(email):
        """
        Generate password reset token for user
        
        Args:
            email: User's email address
            
        Returns:
            PasswordResetToken object if user exists, None otherwise
        """
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = PasswordResetToken.generate_token()
            expires_at = timezone.now() + timedelta(hours=1)
            
            reset_token = PasswordResetToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )
            
            # Send password reset email
            try:
                email_sent = EmailService.send_password_reset_email(
                    email=user.email,
                    reset_token=token,
                    user_name=user.email.split('@')[0]
                )
                
                if not email_sent:
                    logger.warning(f"Failed to send password reset email to {user.email}, but token was created")
            except Exception as e:
                logger.error(f"Exception while sending password reset email to {user.email}: {str(e)}")
                # Continue even if email fails - token is still valid
            
            return reset_token
        except User.DoesNotExist:
            # Return None but don't reveal that email doesn't exist
            return None
    
    @staticmethod
    def confirm_password_reset(token, new_password):
        """
        Confirm password reset and update user password
        
        Args:
            token: Password reset token string
            new_password: New password to set
            
        Returns:
            User object if reset successful, None otherwise
        """
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            
            if reset_token.is_valid():
                user = reset_token.user
                
                # Update password
                user.set_password(new_password)
                user.save()
                
                # Mark token as used
                reset_token.is_used = True
                reset_token.save()
                
                # Invalidate all refresh tokens for this user
                PasswordResetService.invalidate_user_tokens(user)
                
                return user
        except PasswordResetToken.DoesNotExist:
            pass
        
        return None
    
    @staticmethod
    def invalidate_user_tokens(user):
        """
        Invalidate all refresh tokens for user
        
        Args:
            user: User object
        """
        # This would typically involve blacklisting tokens
        # With djangorestframework-simplejwt, we can use the token blacklist
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        
        try:
            # Get all outstanding tokens for user and blacklist them
            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                try:
                    # Blacklist the token
                    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
                    BlacklistedToken.objects.get_or_create(token=token)
                except Exception:
                    pass
        except Exception:
            # If token blacklist is not available, skip
            pass


class AuditLoggingService:
    """Service for logging authentication events"""
    
    @staticmethod
    def log_auth_event(user, email, event_type, ip_address, user_agent, success, details=None):
        """
        Create an authentication log entry
        
        Args:
            user: User object (can be None)
            email: Email address used in attempt
            event_type: Type of authentication event
            ip_address: Client IP address
            user_agent: Client user agent string
            success: Boolean indicating if event was successful
            details: Optional dictionary with additional details
            
        Returns:
            AuthLog object
        """
        if details is None:
            details = {}
        
        log = AuthLog.objects.create(
            user=user,
            email=email,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details
        )
        
        return log
    
    @staticmethod
    def log_login_attempt(user, email, ip_address, user_agent, success):
        """Helper method for logging login attempts"""
        event_type = AuthEventType.LOGIN_SUCCESS if success else AuthEventType.LOGIN_FAILURE
        return AuditLoggingService.log_auth_event(
            user=user,
            email=email,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success
        )
    
    @staticmethod
    def log_otp_generated(user, email, ip_address, user_agent):
        """Helper method for logging OTP generation"""
        return AuditLoggingService.log_auth_event(
            user=user,
            email=email,
            event_type=AuthEventType.OTP_GENERATED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    @staticmethod
    def log_otp_verification(user, email, ip_address, user_agent, success):
        """Helper method for logging OTP verification"""
        event_type = AuthEventType.OTP_VERIFIED if success else AuthEventType.OTP_FAILED
        return AuditLoggingService.log_auth_event(
            user=user,
            email=email,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success
        )
    
    @staticmethod
    def log_password_reset_request(user, email, ip_address, user_agent):
        """Helper method for logging password reset requests"""
        return AuditLoggingService.log_auth_event(
            user=user,
            email=email,
            event_type=AuthEventType.PASSWORD_RESET_REQUESTED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    @staticmethod
    def log_password_reset_completed(user, email, ip_address, user_agent):
        """Helper method for logging password reset completion"""
        return AuditLoggingService.log_auth_event(
            user=user,
            email=email,
            event_type=AuthEventType.PASSWORD_RESET_COMPLETED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )



class RateLimitService:
    """Service for handling rate limiting of authentication attempts"""
    
    # Configuration
    MAX_ATTEMPTS = getattr(settings, 'RATE_LIMIT_ATTEMPTS', 5)
    WINDOW_SECONDS = getattr(settings, 'RATE_LIMIT_WINDOW', 900)  # 15 minutes
    
    @staticmethod
    def _get_ip_key(ip_address):
        """Generate cache key for IP address"""
        return f'rate_limit:ip:{ip_address}'
    
    @staticmethod
    def _get_email_key(email):
        """Generate cache key for email address"""
        return f'rate_limit:email:{email}'
    
    @staticmethod
    def track_failed_attempt(ip_address, email):
        """
        Track a failed login attempt for both IP and email
        
        Args:
            ip_address: Client IP address
            email: Email address used in attempt
            
        Returns:
            Tuple of (ip_count, email_count) after increment
        """
        try:
            ip_key = RateLimitService._get_ip_key(ip_address)
            email_key = RateLimitService._get_email_key(email)
            
            # Increment counters with expiration
            ip_count = cache.get(ip_key, 0) + 1
            email_count = cache.get(email_key, 0) + 1
            
            cache.set(ip_key, ip_count, RateLimitService.WINDOW_SECONDS)
            cache.set(email_key, email_count, RateLimitService.WINDOW_SECONDS)
            
            return ip_count, email_count
        except Exception as e:
            # If Redis is not available, log warning and return 0 (no rate limiting)
            logger.warning(f"Rate limiting unavailable (Redis connection error): {str(e)}")
            return 0, 0
    
    @staticmethod
    def is_rate_limited(ip_address, email):
        """
        Check if IP address or email is rate limited
        
        Args:
            ip_address: Client IP address
            email: Email address to check
            
        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        try:
            ip_key = RateLimitService._get_ip_key(ip_address)
            email_key = RateLimitService._get_email_key(email)
            
            ip_count = cache.get(ip_key, 0)
            email_count = cache.get(email_key, 0)
            
            # Check if either IP or email has exceeded limit
            if ip_count >= RateLimitService.MAX_ATTEMPTS or email_count >= RateLimitService.MAX_ATTEMPTS:
                # Try to get TTL for the key to determine retry-after
                # Note: ttl() is only available in Redis backend, not LocMemCache
                retry_after = RateLimitService.WINDOW_SECONDS
                
                try:
                    if hasattr(cache, 'ttl'):
                        ip_ttl = cache.ttl(ip_key) if ip_count >= RateLimitService.MAX_ATTEMPTS else 0
                        email_ttl = cache.ttl(email_key) if email_count >= RateLimitService.MAX_ATTEMPTS else 0
                        
                        # Use the maximum TTL
                        ttl = max(ip_ttl, email_ttl, 0)
                        
                        # If TTL is available and positive, use it
                        if ttl > 0:
                            retry_after = ttl
                except Exception:
                    # If TTL retrieval fails, use the full window
                    pass
                
                return True, retry_after
            
            return False, 0
        except Exception as e:
            # If Redis is not available, log warning and don't rate limit
            logger.warning(f"Rate limiting unavailable (Redis connection error): {str(e)}")
            return False, 0
    
    @staticmethod
    def reset_counters(ip_address, email):
        """
        Reset failed attempt counters for IP and email on successful login
        
        Args:
            ip_address: Client IP address
            email: Email address
        """
        try:
            ip_key = RateLimitService._get_ip_key(ip_address)
            email_key = RateLimitService._get_email_key(email)
            
            cache.delete(ip_key)
            cache.delete(email_key)
        except Exception as e:
            # If Redis is not available, log warning and continue
            logger.warning(f"Rate limiting unavailable (Redis connection error): {str(e)}")
    
    @staticmethod
    def get_attempt_count(ip_address, email):
        """
        Get current attempt counts for IP and email
        
        Args:
            ip_address: Client IP address
            email: Email address
            
        Returns:
            Tuple of (ip_count, email_count)
        """
        try:
            ip_key = RateLimitService._get_ip_key(ip_address)
            email_key = RateLimitService._get_email_key(email)
            
            ip_count = cache.get(ip_key, 0)
            email_count = cache.get(email_key, 0)
            
            return ip_count, email_count
        except Exception as e:
            # If Redis is not available, log warning and return 0
            logger.warning(f"Rate limiting unavailable (Redis connection error): {str(e)}")
            return 0, 0



class UserCreationService:
    """Service for creating users from approved applications"""
    
    @staticmethod
    def create_user_from_application(application):
        """
        Create a User account from an approved Application
        
        Args:
            application: Application object
            
        Returns:
            Tuple of (User object or None, error_message or None)
        """
        from applications.models import Application
        
        try:
            # Check if User already exists for the Application email
            existing_user = User.objects.filter(email__iexact=application.email).first()
            if existing_user:
                if not existing_user.is_active:
                    existing_user.is_active = True
                    existing_user.first_name = application.first_name or existing_user.first_name
                    existing_user.last_name = application.last_name or existing_user.last_name
                    existing_user.phone_number = application.phone_number or existing_user.phone_number
                    existing_user.national_id_number = application.national_id_number or existing_user.national_id_number
                    existing_user.icpau_registration_number = (
                        application.icpau_certificate_number or existing_user.icpau_registration_number
                    )
                    existing_user.save(update_fields=[
                        'is_active',
                        'first_name',
                        'last_name',
                        'phone_number',
                        'national_id_number',
                        'icpau_registration_number'
                    ])

                    # Link User to Application via foreign key
                    application.user = existing_user
                    application.save(update_fields=['user'])

                    # Create or update profile with application details
                    profile, _ = UserProfile.objects.get_or_create(user=existing_user)
                    profile.first_name = application.first_name or profile.first_name
                    profile.last_name = application.last_name or profile.last_name
                    profile.phone_number = application.phone_number or profile.phone_number
                    profile.address_line_1 = application.address or profile.address_line_1
                    profile.icpau_registration_number = (
                        application.icpau_certificate_number or profile.icpau_registration_number
                    )
                    passport_doc = Document.objects.filter(
                        application=application,
                        document_type='passport_photo'
                    ).first()
                    if passport_doc and not profile.profile_picture:
                        profile.profile_picture = passport_doc.file
                    profile.save()

                    logger.info(
                        f"Reactivated user {existing_user.id} from application {application.id} for {application.email}"
                    )
                    return existing_user, None

                logger.warning(f"User already exists for email {application.email}")
                return None, "User already exists for this email"
            
            raw_or_hashed_password = application.password_hash
            try:
                identify_hasher(raw_or_hashed_password)
                password_to_store = raw_or_hashed_password
            except Exception:
                password_to_store = make_password(raw_or_hashed_password)

            # Create User with email and password_hash from Application
            user = User.objects.create(
                email=application.email,
                password=password_to_store,
                role=UserRole.MEMBER,  # Set role to 2 (member) by default
                is_active=True,
                first_name=application.first_name or '',
                last_name=application.last_name or '',
                phone_number=application.phone_number or '',
                national_id_number=application.national_id_number or '',
                icpau_registration_number=application.icpau_certificate_number or ''
            )

            # Create or update profile with application details
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.first_name = application.first_name or ''
            profile.last_name = application.last_name or ''
            profile.phone_number = application.phone_number or ''
            profile.address_line_1 = application.address or ''
            profile.icpau_registration_number = application.icpau_certificate_number or ''
            passport_doc = Document.objects.filter(
                application=application,
                document_type='passport_photo'
            ).first()
            if not passport_doc:
                passport_doc = Document.objects.filter(
                    application=application,
                    file_name__icontains='passport'
                ).first()
            if passport_doc and not profile.profile_picture:
                if passport_doc.file and passport_doc.file.storage.exists(passport_doc.file.name):
                    profile.profile_picture = passport_doc.file
            profile.save()
            
            # Link User to Application via foreign key
            application.user = user
            application.save()
            
            logger.info(f"Created user {user.id} from application {application.id} for {application.email}")
            
            return user, None
            
        except Exception as e:
            error_msg = f"Error creating user from application: {str(e)}"
            logger.error(error_msg)
            return None, error_msg



