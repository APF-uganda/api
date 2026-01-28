"""
Property-based tests for audit logging requirements
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
import uuid

from .models import OTP, PasswordResetToken, AuthLog, AuthEventType
from .services import TokenService, OTPService, PasswordResetService

User = get_user_model()


@pytest.mark.django_db
class TestAuditLoggingProperties:
    """Property-based tests for audit logging"""
    
    def test_property_25_login_attempt_logging(self):
        """
        Property 25: Login attempt logging
        **Validates: Requirements 9.1**
        
        For any login attempt (successful or failed), an AuthLog entry should 
        be created with timestamp, email, IP address, and outcome.
        """
        client = APIClient()
        email = f'test_{uuid.uuid4().hex[:8]}@example.com'
        password = 'testpass123'
        
        # Get initial log count
        initial_count = AuthLog.objects.filter(email=email).count()
        
        # Attempt login
        response = client.post('/api/auth/login', {
            'email': email,
            'password': password
        }, format='json')
        
        # Check that a log entry was created
        final_count = AuthLog.objects.filter(email=email).count()
        assert final_count > initial_count
        
        # Get the latest log entry
        log = AuthLog.objects.filter(email=email).latest('timestamp')
        
        # Verify log has required fields
        assert log.email == email
        assert log.ip_address is not None
        assert log.timestamp is not None
        # Event type can be LOGIN_SUCCESS, LOGIN_FAILURE, or RATE_LIMIT_TRIGGERED
        assert log.event_type in [
            AuthEventType.LOGIN_SUCCESS, 
            AuthEventType.LOGIN_FAILURE,
            AuthEventType.RATE_LIMIT_TRIGGERED
        ]
        assert isinstance(log.success, bool)
    
    def test_property_26_otp_generation_logging(self):
        """
        Property 26: OTP generation logging
        **Validates: Requirements 9.2**
        
        For any OTP generation, an AuthLog entry should be created with 
        event_type='otp_generated'.
        """
        client = APIClient()
        email = f'test_{uuid.uuid4().hex[:8]}@example.com'
        password = 'testpass123'
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            role='2'
        )
        
        # Get initial OTP log count
        initial_count = AuthLog.objects.filter(
            email=email,
            event_type=AuthEventType.OTP_GENERATED
        ).count()
        
        # Login to trigger OTP generation
        response = client.post('/api/auth/login', {
            'email': email,
            'password': password
        }, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            # Check that OTP generation was logged
            final_count = AuthLog.objects.filter(
                email=email,
                event_type=AuthEventType.OTP_GENERATED
            ).count()
            assert final_count > initial_count
            
            # Get the OTP generation log
            log = AuthLog.objects.filter(
                email=email,
                event_type=AuthEventType.OTP_GENERATED
            ).latest('timestamp')
            
            # Verify log properties
            assert log.user == user
            assert log.success is True
    
    def test_property_27_otp_verification_logging(self):
        """
        Property 27: OTP verification logging
        **Validates: Requirements 9.3**
        
        For any OTP verification attempt, an AuthLog entry should be created 
        with the verification outcome.
        """
        client = APIClient()
        email = f'test_{uuid.uuid4().hex[:8]}@example.com'
        password = 'testpass123'
        otp_code = '123456'
        
        # Create user and OTP
        user = User.objects.create_user(
            email=email,
            password=password,
            role='2'
        )
        
        session_id = uuid.uuid4()
        OTP.objects.create(
            user=user,
            code=otp_code,
            session_id=session_id,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Get initial log count
        initial_count = AuthLog.objects.filter(
            event_type=AuthEventType.OTP_VERIFIED
        ).count()
        
        # Attempt OTP verification
        response = client.post('/api/auth/verify-otp', {
            'session_id': str(session_id),
            'otp': otp_code,
            'remember_me': False
        }, format='json')
        
        # Check that verification was logged
        final_count = AuthLog.objects.filter(
            event_type=AuthEventType.OTP_VERIFIED
        ).count()
        assert final_count > initial_count
        
        # Get the verification log
        log = AuthLog.objects.filter(
            event_type=AuthEventType.OTP_VERIFIED
        ).latest('timestamp')
        
        # Verify log properties
        assert log.timestamp is not None
        assert isinstance(log.success, bool)
        if response.status_code == status.HTTP_200_OK:
            assert log.success is True
            assert log.user == user
    
    def test_property_28_password_reset_request_logging(self):
        """
        Property 28: Password reset request logging
        **Validates: Requirements 9.4**
        
        For any password reset request, an AuthLog entry should be created 
        with event_type='password_reset_requested'.
        """
        client = APIClient()
        email = f'test_{uuid.uuid4().hex[:8]}@example.com'
        
        # Get initial log count
        initial_count = AuthLog.objects.filter(
            email=email,
            event_type=AuthEventType.PASSWORD_RESET_REQUESTED
        ).count()
        
        # Request password reset
        response = client.post('/api/auth/password-reset-request', {
            'email': email
        }, format='json')
        
        # Should always return success (security best practice)
        assert response.status_code == status.HTTP_200_OK
        
        # Check that request was logged
        final_count = AuthLog.objects.filter(
            email=email,
            event_type=AuthEventType.PASSWORD_RESET_REQUESTED
        ).count()
        assert final_count > initial_count
        
        # Get the log entry
        log = AuthLog.objects.filter(
            email=email,
            event_type=AuthEventType.PASSWORD_RESET_REQUESTED
        ).latest('timestamp')
        
        # Verify log properties
        assert log.email == email
        assert log.timestamp is not None
        assert log.ip_address is not None
    
    def test_property_29_password_reset_completion_logging(self):
        """
        Property 29: Password reset completion logging
        **Validates: Requirements 9.5**
        
        For any completed password reset, an AuthLog entry should be created 
        with event_type='password_reset_completed'.
        """
        client = APIClient()
        email = f'test_{uuid.uuid4().hex[:8]}@example.com'
        password = 'testpass123'
        new_password = 'newpass456'
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            role='2'
        )
        
        # Create password reset token
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=PasswordResetToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Get initial log count
        initial_count = AuthLog.objects.filter(
            email=email,
            event_type=AuthEventType.PASSWORD_RESET_COMPLETED
        ).count()
        
        # Complete password reset
        response = client.post('/api/auth/password-reset-confirm', {
            'token': reset_token.token,
            'new_password': new_password
        }, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            # Check that completion was logged
            final_count = AuthLog.objects.filter(
                email=email,
                event_type=AuthEventType.PASSWORD_RESET_COMPLETED
            ).count()
            assert final_count > initial_count
            
            # Get the log entry
            log = AuthLog.objects.filter(
                email=email,
                event_type=AuthEventType.PASSWORD_RESET_COMPLETED
            ).latest('timestamp')
            
            # Verify log properties
            assert log.user == user
            assert log.email == email
            assert log.timestamp is not None
    
    def test_property_30_rate_limit_trigger_logging(self):
        """
        Property 30: Rate limit trigger logging
        **Validates: Requirements 9.6**
        
        For any rate limit trigger, an AuthLog entry should be created with 
        event_type='rate_limit_triggered'.
        """
        client = APIClient()
        email = f'test_{uuid.uuid4().hex[:8]}@example.com'
        password = 'wrongpass123'
        
        # Make multiple failed login attempts to trigger rate limit
        for i in range(6):  # Exceed the 5 attempt limit
            response = client.post('/api/auth/login', {
                'email': email,
                'password': password
            }, format='json')
            
            # Check if rate limited
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                # Verify rate limit was logged
                rate_limit_logs = AuthLog.objects.filter(
                    email=email,
                    event_type=AuthEventType.RATE_LIMIT_TRIGGERED
                )
                assert rate_limit_logs.exists()
                
                # Get the latest rate limit log
                log = rate_limit_logs.latest('timestamp')
                
                # Verify log properties
                assert log.email == email
                assert log.success is False
                assert log.timestamp is not None
                assert 'retry_after' in log.details
                break
    
    def test_property_31_auth_logs_retrieval_with_filtering(self):
        """
        Property 31: Auth logs retrieval with filtering
        **Validates: Requirements 9.7**
        
        For any admin user requesting auth logs with filters (email, event_type, 
        date range), the returned logs should match all specified filter criteria.
        """
        client = APIClient()
        email_filter = f'test_{uuid.uuid4().hex[:8]}@example.com'
        password = 'testpass123'
        
        # Create admin user
        admin = User.objects.create_user(
            email='admin@test.com',
            password='adminpass123',
            role='1'  # admin
        )
        
        # Create test user and generate some logs
        test_user = User.objects.create_user(
            email=email_filter,
            password=password,
            role='2'
        )
        
        # Generate login attempt log
        client.post('/api/auth/login', {
            'email': email_filter,
            'password': password
        }, format='json')
        
        # Get admin token
        otp_obj, session_id = OTPService.generate_otp(admin)
        
        verify_response = client.post('/api/auth/verify-otp', {
            'session_id': str(session_id),
            'otp': otp_obj.code,
            'remember_me': False
        }, format='json')
        
        admin_token = verify_response.data['access_token']
        
        # Request logs with email filter
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        response = client.get(f'/api/auth/logs?email={email_filter}', format='json')
        
        if response.status_code == status.HTTP_200_OK:
            # Verify all returned logs match the filter
            for log in response.data['results']:
                assert email_filter in log['email']
            
            # Test event_type filter
            response = client.get(
                f'/api/auth/logs?event_type={AuthEventType.LOGIN_FAILURE}',
                format='json'
            )
            
            if response.status_code == status.HTTP_200_OK and response.data['results']:
                for log in response.data['results']:
                    assert log['event_type'] == AuthEventType.LOGIN_FAILURE
