import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone
import uuid

from .models import OTP, PasswordResetToken, AuthLog, AuthEventType
from .services import TokenService

User = get_user_model()


@pytest.mark.django_db
class TestLoginView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/login'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
    
    @patch('authentication.views.OTPService.generate_otp')
    def test_login_with_valid_credentials(self, mock_generate_otp):
        """Test login with valid email and password"""
        mock_generate_otp.return_value = uuid.uuid4()
        
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'session_id' in response.data
        assert response.data['message'] == 'OTP sent to your email'
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid password"""
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'INVALID_CREDENTIALS'
    
    def test_login_with_nonexistent_email(self):
        """Test login with non-existent email"""
        response = self.client.post(self.url, {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'INVALID_CREDENTIALS'
    
    def test_login_missing_email(self):
        """Test login without email"""
        response = self.client.post(self.url, {
            'password': 'testpass123'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'VALIDATION_ERROR'
    
    def test_login_missing_password(self):
        """Test login without password"""
        response = self.client.post(self.url, {
            'email': 'test@example.com'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'VALIDATION_ERROR'


@pytest.mark.django_db
class TestVerifyOTPView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/verify-otp'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
        self.session_id = uuid.uuid4()
        self.otp = OTP.objects.create(
            user=self.user,
            code='123456',
            session_id=self.session_id,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
    
    def test_verify_otp_with_valid_code(self):
        """Test OTP verification with valid code"""
        response = self.client.post(self.url, {
            'session_id': str(self.session_id),
            'otp': '123456',
            'remember_me': False
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'access_token' in response.data
        assert 'refresh_token' in response.data
        assert response.data['user']['email'] == 'test@example.com'
        assert response.data['user']['role'] == '2'
    
    def test_verify_otp_with_invalid_code(self):
        """Test OTP verification with invalid code"""
        response = self.client.post(self.url, {
            'session_id': str(self.session_id),
            'otp': '999999',
            'remember_me': False
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'INVALID_OTP'
    
    def test_verify_otp_with_expired_code(self):
        """Test OTP verification with expired code"""
        self.otp.expires_at = timezone.now() - timedelta(minutes=1)
        self.otp.save()
        
        response = self.client.post(self.url, {
            'session_id': str(self.session_id),
            'otp': '123456',
            'remember_me': False
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['success'] is False
    
    def test_verify_otp_missing_session_id(self):
        """Test OTP verification without session_id"""
        response = self.client.post(self.url, {
            'otp': '123456'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
    
    def test_verify_otp_with_remember_me(self):
        """Test OTP verification with remember_me flag"""
        response = self.client.post(self.url, {
            'session_id': str(self.session_id),
            'otp': '123456',
            'remember_me': True
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'refresh_token' in response.data


@pytest.mark.django_db
class TestRefreshTokenView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/refresh'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
        tokens = TokenService.generate_tokens(self.user, remember_me=False)
        self.refresh_token = tokens['refresh_token']
    
    def test_refresh_token_with_valid_token(self):
        """Test token refresh with valid refresh token"""
        response = self.client.post(self.url, {
            'refresh_token': self.refresh_token
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'access_token' in response.data
    
    def test_refresh_token_with_invalid_token(self):
        """Test token refresh with invalid token"""
        response = self.client.post(self.url, {
            'refresh_token': 'invalid_token'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['success'] is False
    
    def test_refresh_token_missing_token(self):
        """Test token refresh without token"""
        response = self.client.post(self.url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False


@pytest.mark.django_db
class TestLogoutView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/logout'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
        tokens = TokenService.generate_tokens(self.user, remember_me=False)
        self.access_token = tokens['access_token']
        self.refresh_token = tokens['refresh_token']
    
    def test_logout_with_valid_token(self):
        """Test logout with valid access token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.post(self.url, {
            'refresh_token': self.refresh_token
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['message'] == 'Logged out successfully'
    
    def test_logout_without_authentication(self):
        """Test logout without authentication"""
        response = self.client.post(self.url, {
            'refresh_token': self.refresh_token
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_logout_missing_refresh_token(self):
        """Test logout without refresh token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.post(self.url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCurrentUserView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/me'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
        tokens = TokenService.generate_tokens(self.user, remember_me=False)
        self.access_token = tokens['access_token']
    
    def test_get_current_user_with_valid_token(self):
        """Test getting current user info with valid token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'test@example.com'
        assert response.data['role'] == '2'
        assert 'id' in response.data
        assert 'created_at' in response.data
    
    def test_get_current_user_without_authentication(self):
        """Test getting current user without authentication"""
        response = self.client.get(self.url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPasswordResetRequestView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/password-reset-request'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
    
    @patch('authentication.views.PasswordResetService.request_password_reset')
    def test_password_reset_request_with_valid_email(self, mock_request_reset):
        """Test password reset request with valid email"""
        mock_request_reset.return_value = None
        
        response = self.client.post(self.url, {
            'email': 'test@example.com'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'Password reset instructions' in response.data['message']
    
    def test_password_reset_request_with_nonexistent_email(self):
        """Test password reset request with non-existent email (should still return success)"""
        response = self.client.post(self.url, {
            'email': 'nonexistent@example.com'
        }, format='json')
        
        # Should return success for security (don't reveal if email exists)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
    
    def test_password_reset_request_missing_email(self):
        """Test password reset request without email"""
        response = self.client.post(self.url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False


@pytest.mark.django_db
class TestPasswordResetConfirmView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/password-reset-confirm'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='2'
        )
        self.reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token=PasswordResetToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
    
    def test_password_reset_confirm_with_valid_token(self):
        """Test password reset with valid token"""
        response = self.client.post(self.url, {
            'token': self.reset_token.token,
            'new_password': 'newpassword123'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['message'] == 'Password reset successfully'
        
        # Verify password was changed
        self.user.refresh_from_db()
        assert self.user.check_password('newpassword123')
    
    def test_password_reset_confirm_with_invalid_token(self):
        """Test password reset with invalid token"""
        response = self.client.post(self.url, {
            'token': 'invalid_token',
            'new_password': 'newpassword123'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['success'] is False
    
    def test_password_reset_confirm_with_expired_token(self):
        """Test password reset with expired token"""
        self.reset_token.expires_at = timezone.now() - timedelta(hours=1)
        self.reset_token.save()
        
        response = self.client.post(self.url, {
            'token': self.reset_token.token,
            'new_password': 'newpassword123'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_password_reset_confirm_with_short_password(self):
        """Test password reset with password too short"""
        response = self.client.post(self.url, {
            'token': self.reset_token.token,
            'new_password': 'short'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'at least 8 characters' in response.data['error']['message']
    
    def test_password_reset_confirm_missing_fields(self):
        """Test password reset without required fields"""
        response = self.client.post(self.url, {
            'token': self.reset_token.token
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAuthLogsView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/logs'
        
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
        AuthLog.objects.create(
            user=self.member_user,
            email='member@example.com',
            event_type=AuthEventType.LOGIN_FAILURE,
            ip_address='192.168.1.2',
            success=False
        )
    
    def test_auth_logs_as_admin(self):
        """Test retrieving auth logs as admin"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        response = self.client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 2
    
    def test_auth_logs_as_member(self):
        """Test retrieving auth logs as member (should be forbidden)"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.member_token}')
        
        response = self.client.get(self.url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error']['code'] == 'FORBIDDEN'
    
    def test_auth_logs_without_authentication(self):
        """Test retrieving auth logs without authentication"""
        response = self.client.get(self.url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_auth_logs_with_email_filter(self):
        """Test retrieving auth logs with email filter"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        response = self.client.get(f'{self.url}?email=admin@example.com')
        
        assert response.status_code == status.HTTP_200_OK
        assert all('admin@example.com' in log['email'] for log in response.data['results'])
    
    def test_auth_logs_with_event_type_filter(self):
        """Test retrieving auth logs with event type filter"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        response = self.client.get(f'{self.url}?event_type={AuthEventType.LOGIN_SUCCESS}')
        
        assert response.status_code == status.HTTP_200_OK
        assert all(log['event_type'] == AuthEventType.LOGIN_SUCCESS for log in response.data['results'])
    
    def test_auth_logs_pagination(self):
        """Test auth logs pagination"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        response = self.client.get(f'{self.url}?page=1&page_size=1')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert 'next' in response.data
