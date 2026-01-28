"""
Integration tests for complete authentication flows.

These tests verify end-to-end authentication scenarios including:
- Complete login flow (login → OTP → access protected endpoint)
- Token refresh flow
- Password reset flow
- Rate limiting flow
- Role-based access control
- Application-to-User registration flow

Requirements: 1.1, 2.4, 3.1-3.4, 4.6, 4.7, 6.1, 6.4, 6.7, 8.2, 8.4, 8.5, 12.1-12.4
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
import uuid
import time

from .models import OTP, PasswordResetToken, AuthLog, AuthEventType
from .services import TokenService
from applications.models import Application

User = get_user_model()


@pytest.mark.django_db
class TestCompleteLoginFlow(TestCase):
    """
    Test complete login flow: POST /api/auth/login → POST /api/auth/verify-otp → GET /api/auth/me
    
    Requirements: 1.1, 2.4, 3.4
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
    
    @patch('authentication.services.EmailService.send_otp_email')
    def test_complete_login_flow_success(self, mock_send_email):
        """Test complete login flow from credentials to accessing protected endpoint"""
        mock_send_email.return_value = True
        
        # Step 1: Login with credentials
        login_response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'testpass123'
        }, format='json')
        
        assert login_response.status_code == status.HTTP_200_OK
        assert login_response.data['success'] is True
        assert 'session_id' in login_response.data
        
        # The session_id in response might be a string representation of a tuple
        # Extract the actual UUID session_id
        session_id_str = login_response.data['session_id']
        
        # Get the OTP from database using the user
        otp = OTP.objects.filter(user=self.user, is_used=False).order_by('-created_at').first()
        assert otp is not None
        
        # Step 2: Verify OTP
        verify_response = self.client.post('/api/auth/verify-otp', {
            'session_id': str(otp.session_id),
            'otp': otp.code,
            'remember_me': False
        }, format='json')
        
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.data['success'] is True
        assert 'access_token' in verify_response.data
        assert 'refresh_token' in verify_response.data
        assert verify_response.data['user']['email'] == 'test@example.com'
        assert verify_response.data['user']['role'] == '2'
        
        access_token = verify_response.data['access_token']
        
        # Step 3: Access protected endpoint with JWT
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        me_response = self.client.get('/api/auth/me')
        
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.data['email'] == 'test@example.com'
        assert me_response.data['role'] == '2'
        assert 'id' in me_response.data
        assert 'created_at' in me_response.data
    
    @patch('authentication.services.EmailService.send_otp_email')
    def test_complete_login_flow_with_remember_me(self, mock_send_email):
        """Test complete login flow with remember_me flag"""
        mock_send_email.return_value = True
        
        # Step 1: Login
        login_response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'testpass123'
        }, format='json')
        
        # Get the OTP from database using the user
        otp = OTP.objects.filter(user=self.user, is_used=False).order_by('-created_at').first()
        
        # Step 2: Verify OTP with remember_me=True
        verify_response = self.client.post('/api/auth/verify-otp', {
            'session_id': str(otp.session_id),
            'otp': otp.code,
            'remember_me': True
        }, format='json')
        
        assert verify_response.status_code == status.HTTP_200_OK
        assert 'refresh_token' in verify_response.data
        
        # Verify refresh token has extended expiration (30 days)
        # This is validated by the token service property tests
    
    def test_login_flow_fails_with_invalid_credentials(self):
        """Test login flow fails with invalid credentials"""
        login_response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, format='json')
        
        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert login_response.data['success'] is False
        assert login_response.data['error']['code'] == 'INVALID_CREDENTIALS'
    
    @patch('authentication.services.EmailService.send_otp_email')
    def test_login_flow_fails_with_invalid_otp(self, mock_send_email):
        """Test login flow fails with invalid OTP"""
        mock_send_email.return_value = True
        
        # Step 1: Login
        login_response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'testpass123'
        }, format='json')
        
        # Get the OTP from database
        otp = OTP.objects.filter(user=self.user, is_used=False).order_by('-created_at').first()
        
        # Step 2: Try to verify with wrong OTP
        verify_response = self.client.post('/api/auth/verify-otp', {
            'session_id': str(otp.session_id),
            'otp': '999999',
            'remember_me': False
        }, format='json')
        
        assert verify_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert verify_response.data['success'] is False
    
    def test_protected_endpoint_fails_without_token(self):
        """Test accessing protected endpoint without authentication fails"""
        me_response = self.client.get('/api/auth/me')
        
        assert me_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefreshFlow(TestCase):
    """
    Test token refresh flow: POST /api/auth/verify-otp → POST /api/auth/refresh
    
    Requirements: 4.6, 4.7
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
    
    @patch('authentication.services.EmailService.send_otp_email')
    def test_token_refresh_flow_success(self, mock_send_email):
        """Test complete token refresh flow"""
        mock_send_email.return_value = True
        
        # Step 1: Complete login to get tokens
        login_response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'testpass123'
        }, format='json')
        
        otp = OTP.objects.filter(user=self.user, is_used=False).order_by('-created_at').first()
        
        verify_response = self.client.post('/api/auth/verify-otp', {
            'session_id': str(otp.session_id),
            'otp': otp.code,
            'remember_me': False
        }, format='json')
        
        old_access_token = verify_response.data['access_token']
        refresh_token = verify_response.data['refresh_token']
        
        # Step 2: Refresh the access token
        refresh_response = self.client.post('/api/auth/refresh', {
            'refresh_token': refresh_token
        }, format='json')
        
        assert refresh_response.status_code == status.HTTP_200_OK
        assert refresh_response.data['success'] is True
        assert 'access_token' in refresh_response.data
        
        new_access_token = refresh_response.data['access_token']
        
        # Verify new token is different from old token
        assert new_access_token != old_access_token
        
        # Step 3: Verify new access token works
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
        me_response = self.client.get('/api/auth/me')
        
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.data['email'] == 'test@example.com'
    
    def test_token_refresh_fails_with_invalid_token(self):
        """Test token refresh fails with invalid refresh token"""
        refresh_response = self.client.post('/api/auth/refresh', {
            'refresh_token': 'invalid_token'
        }, format='json')
        
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert refresh_response.data['success'] is False


@pytest.mark.django_db
class TestPasswordResetFlow(TestCase):
    """
    Test password reset flow: POST /api/auth/password-reset-request → 
    POST /api/auth/password-reset-confirm → POST /api/auth/login
    
    Requirements: 6.1, 6.4, 6.7
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='oldpassword123',
            role='2'
        )
    
    @patch('authentication.services.EmailService.send_password_reset_email')
    @patch('authentication.services.EmailService.send_otp_email')
    def test_complete_password_reset_flow(self, mock_send_otp, mock_send_reset):
        """Test complete password reset flow"""
        mock_send_reset.return_value = True
        mock_send_otp.return_value = True
        
        # Step 1: Request password reset
        reset_request_response = self.client.post('/api/auth/password-reset-request', {
            'email': 'test@example.com'
        }, format='json')
        
        assert reset_request_response.status_code == status.HTTP_200_OK
        assert reset_request_response.data['success'] is True
        
        # Get the reset token from database (in real scenario, user gets it via email)
        reset_token = PasswordResetToken.objects.filter(user=self.user, is_used=False).first()
        assert reset_token is not None
        
        # Step 2: Confirm password reset with new password
        reset_confirm_response = self.client.post('/api/auth/password-reset-confirm', {
            'token': reset_token.token,
            'new_password': 'newpassword123'
        }, format='json')
        
        assert reset_confirm_response.status_code == status.HTTP_200_OK
        assert reset_confirm_response.data['success'] is True
        assert reset_confirm_response.data['message'] == 'Password reset successfully'
        
        # Step 3: Verify old password no longer works
        old_login_response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'oldpassword123'
        }, format='json')
        
        assert old_login_response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Step 4: Verify new password works
        new_login_response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'newpassword123'
        }, format='json')
        
        assert new_login_response.status_code == status.HTTP_200_OK
        assert new_login_response.data['success'] is True
        assert 'session_id' in new_login_response.data
    
    @patch('authentication.services.EmailService.send_password_reset_email')
    def test_password_reset_invalidates_refresh_tokens(self, mock_send_reset):
        """Test that password reset invalidates all existing refresh tokens"""
        mock_send_reset.return_value = True
        
        # Create a refresh token before password reset
        tokens = TokenService.generate_tokens(self.user, remember_me=False)
        old_refresh_token = tokens['refresh_token']
        
        # Request and confirm password reset
        self.client.post('/api/auth/password-reset-request', {
            'email': 'test@example.com'
        }, format='json')
        
        reset_token = PasswordResetToken.objects.filter(user=self.user, is_used=False).first()
        
        self.client.post('/api/auth/password-reset-confirm', {
            'token': reset_token.token,
            'new_password': 'newpassword123'
        }, format='json')
        
        # Try to use old refresh token (should fail)
        refresh_response = self.client.post('/api/auth/refresh', {
            'refresh_token': old_refresh_token
        }, format='json')
        
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRateLimitingFlow(TestCase):
    """
    Test rate limiting flow: Multiple failed POST /api/auth/login → 429 response → 
    Wait → Successful login
    
    Requirements: 8.2, 8.4, 8.5
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
    
    def test_rate_limiting_blocks_after_threshold(self):
        """Test that rate limiting blocks attempts after threshold"""
        # Make 5 failed login attempts (threshold)
        for i in range(5):
            response = self.client.post('/api/auth/login', {
                'email': 'test@example.com',
                'password': 'wrongpassword'
            }, format='json')
            
            if i < 4:
                # First 4 attempts should return 401
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # 6th attempt should be rate limited
        response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.data['error']['code'] == 'RATE_LIMIT_EXCEEDED'
        
        # Verify rate limit event was logged
        rate_limit_log = AuthLog.objects.filter(
            email='test@example.com',
            event_type=AuthEventType.RATE_LIMIT_TRIGGERED
        ).exists()
        assert rate_limit_log
    
    @patch('authentication.services.EmailService.send_otp_email')
    def test_successful_login_resets_rate_limit(self, mock_send_email):
        """Test that successful login resets rate limit counters"""
        mock_send_email.return_value = True
        
        # Make 3 failed attempts
        for i in range(3):
            self.client.post('/api/auth/login', {
                'email': 'test@example.com',
                'password': 'wrongpassword'
            }, format='json')
        
        # Make successful login
        success_response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'testpass123'
        }, format='json')
        
        assert success_response.status_code == status.HTTP_200_OK
        
        # Make 5 more failed attempts - should not be rate limited yet
        # because counter was reset
        for i in range(5):
            response = self.client.post('/api/auth/login', {
                'email': 'test@example.com',
                'password': 'wrongpassword'
            }, format='json')
            
            if i < 4:
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # 6th attempt after reset should be rate limited
        response = self.client.post('/api/auth/login', {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
class TestRoleBasedAccessControl(TestCase):
    """
    Test role-based access control: Create admin and member users, verify admin can 
    access /api/auth/logs, verify member cannot access /api/auth/logs
    
    Requirements: 3.1, 3.2, 3.3, 3.4
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            role='1'
        )
        admin_tokens = TokenService.generate_tokens(self.admin_user, remember_me=False)
        self.admin_token = admin_tokens['access_token']
        
        # Create member user
        self.member_user = User.objects.create_user(
            email='member@example.com',
            password='memberpass123',
            role='2'
        )
        member_tokens = TokenService.generate_tokens(self.member_user, remember_me=False)
        self.member_token = member_tokens['access_token']
        
        # Create some auth logs
        AuthLog.objects.create(
            user=self.admin_user,
            email='admin@example.com',
            event_type=AuthEventType.LOGIN_SUCCESS,
            ip_address='192.168.1.1',
            success=True
        )
    
    def test_admin_can_access_auth_logs(self):
        """Test that admin user can access auth logs endpoint"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        response = self.client.get('/api/auth/logs')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 1
    
    def test_member_cannot_access_auth_logs(self):
        """Test that member user cannot access auth logs endpoint"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.member_token}')
        
        response = self.client.get('/api/auth/logs')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error']['code'] == 'FORBIDDEN'
    
    def test_unauthenticated_cannot_access_auth_logs(self):
        """Test that unauthenticated user cannot access auth logs endpoint"""
        response = self.client.get('/api/auth/logs')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch('authentication.services.EmailService.send_otp_email')
    def test_admin_role_in_login_response(self, mock_send_email):
        """Test that admin role is correctly returned in login response"""
        mock_send_email.return_value = True
        
        # Login as admin
        login_response = self.client.post('/api/auth/login', {
            'email': 'admin@example.com',
            'password': 'adminpass123'
        }, format='json')
        
        otp = OTP.objects.filter(user=self.admin_user, is_used=False).order_by('-created_at').first()
        
        verify_response = self.client.post('/api/auth/verify-otp', {
            'session_id': str(otp.session_id),
            'otp': otp.code,
            'remember_me': False
        }, format='json')
        
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.data['user']['role'] == '1'
    
    @patch('authentication.services.EmailService.send_otp_email')
    def test_member_role_in_login_response(self, mock_send_email):
        """Test that member role is correctly returned in login response"""
        mock_send_email.return_value = True
        
        # Login as member
        login_response = self.client.post('/api/auth/login', {
            'email': 'member@example.com',
            'password': 'memberpass123'
        }, format='json')
        
        otp = OTP.objects.filter(user=self.member_user, is_used=False).order_by('-created_at').first()
        
        verify_response = self.client.post('/api/auth/verify-otp', {
            'session_id': str(otp.session_id),
            'otp': otp.code,
            'remember_me': False
        }, format='json')
        
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.data['user']['role'] == '2'


@pytest.mark.django_db
class TestApplicationToUserRegistrationFlow(TestCase):
    """
    Test Application-to-User registration flow: POST /api/applications/ → 
    Admin approves application → Verify User account is automatically created → 
    POST /api/auth/login with application credentials → Verify login succeeds and returns role=2
    
    Requirements: 12.1, 12.2, 12.3, 12.4
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Create admin user for approving applications
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            role='1',
            is_staff=True
        )
    
    @patch('authentication.services.EmailService.send_otp_email')
    def test_complete_application_to_user_flow(self, mock_send_email):
        """Test complete flow from application submission to login"""
        mock_send_email.return_value = True
        
        # Step 1: Create application
        application_data = {
            'username': 'newmember',
            'email': 'newmember@example.com',
            'password_hash': 'memberpass123',
            'first_name': 'New',
            'last_name': 'Member',
            'date_of_birth': '1990-01-01',
            'phone_number': '256700000000',
            'address': '123 Test Street',
            'payment_method': 'mtn',
            'payment_phone': '256700000000'
        }
        
        create_response = self.client.post('/api/applications/', application_data, format='json')
        
        assert create_response.status_code == status.HTTP_201_CREATED
        application_id = create_response.data['id']
        
        # Verify User does not exist yet
        assert not User.objects.filter(email='newmember@example.com').exists()
        
        # Step 2: Admin approves application
        application = Application.objects.get(id=application_id)
        application.status = 'approved'
        application.save()
        
        # Step 3: Verify User account was automatically created
        user = User.objects.filter(email='newmember@example.com').first()
        assert user is not None
        assert user.role == '2'  # Member role
        assert user.is_active is True
        
        # Verify User is linked to Application
        application.refresh_from_db()
        assert application.user == user
        
        # Step 4: Login with application credentials
        login_response = self.client.post('/api/auth/login', {
            'email': 'newmember@example.com',
            'password': 'memberpass123'
        }, format='json')
        
        assert login_response.status_code == status.HTTP_200_OK
        assert login_response.data['success'] is True
        assert 'session_id' in login_response.data
        
        otp = OTP.objects.filter(user=user, is_used=False).order_by('-created_at').first()
        
        # Step 5: Verify OTP and check role
        verify_response = self.client.post('/api/auth/verify-otp', {
            'session_id': str(otp.session_id),
            'otp': otp.code,
            'remember_me': False
        }, format='json')
        
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.data['success'] is True
        assert verify_response.data['user']['email'] == 'newmember@example.com'
        assert verify_response.data['user']['role'] == '2'  # Member role
    
    def test_duplicate_user_prevention(self):
        """Test that duplicate User creation is prevented"""
        # Create application
        application_data = {
            'username': 'duplicate',
            'email': 'duplicate@example.com',
            'password_hash': 'password123',
            'first_name': 'Duplicate',
            'last_name': 'User',
            'date_of_birth': '1990-01-01',
            'phone_number': '256700000001',
            'address': '123 Test Street',
            'payment_method': 'mtn',
            'payment_phone': '256700000001'
        }
        
        self.client.post('/api/applications/', application_data, format='json')
        
        # Manually create User with same email
        User.objects.create_user(
            email='duplicate@example.com',
            password='password123',
            role='2'
        )
        
        # Approve application (should not create duplicate User)
        application = Application.objects.get(email='duplicate@example.com')
        application.status = 'approved'
        application.save()
        
        # Verify only one User exists
        user_count = User.objects.filter(email='duplicate@example.com').count()
        assert user_count == 1
    
    def test_password_hashing_in_application(self):
        """Test that password is hashed when application is created"""
        application_data = {
            'username': 'hasheduser',
            'email': 'hashed@example.com',
            'password_hash': 'plainpassword123',
            'first_name': 'Hashed',
            'last_name': 'User',
            'date_of_birth': '1990-01-01',
            'phone_number': '256700000002',
            'address': '123 Test Street',
            'payment_method': 'mtn',
            'payment_phone': '256700000002'
        }
        
        create_response = self.client.post('/api/applications/', application_data, format='json')
        
        assert create_response.status_code == status.HTTP_201_CREATED
        
        # Verify password is hashed in database
        application = Application.objects.get(email='hashed@example.com')
        assert application.password_hash != 'plainpassword123'
        assert application.password_hash.startswith('pbkdf2_sha256$')
