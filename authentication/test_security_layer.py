"""
Tests for the security layer implementation
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class SecurityLayerTestCase(TestCase):
    """
    Test suite for authentication and authorization security layer
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='AdminPass123!',
            role='1'  # Admin
        )
        
        self.member_user = User.objects.create_user(
            email='member@test.com',
            password='MemberPass123!',
            role='2'  # Member
        )
        
        # Generate tokens for users
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.member_token = str(RefreshToken.for_user(self.member_user).access_token)
    
    def test_public_endpoints_accessible_without_auth(self):
        """Test that public endpoints are accessible without authentication"""
        
        # Health check
        response = self.client.get('/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Login endpoint (with proper JSON format)
        response = self.client.post('/api/auth/login', 
            {'email': 'test@example.com', 'password': 'password'},
            format='json'
        )
        # Should return 401 for invalid credentials, not 403 for auth required
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST])
        
        # Contact submission (with proper JSON format)
        response = self.client.post('/api/contacts/submit/', 
            {
                'name': 'Test User',
                'email': 'test@example.com',
                'subject': 'Test',
                'message': 'Test message'
            },
            format='json'
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
    
    def test_protected_endpoints_require_auth(self):
        """Test that protected endpoints require authentication"""
        
        # Try to access admin endpoint without auth
        response = self.client.get('/api/applications/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to access contact list without auth
        response = self.client.get('/api/contacts/list/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to access auth logs without auth
        response = self.client.get('/api/auth/logs')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_can_access_admin_endpoints(self):
        """Test that admin users can access admin-only endpoints"""
        
        # Set admin token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Access applications list
        response = self.client.get('/api/applications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Access contact messages list
        response = self.client.get('/api/contacts/list/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Access auth logs
        response = self.client.get('/api/auth/logs')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_member_cannot_access_admin_endpoints(self):
        """Test that member users cannot access admin-only endpoints"""
        
        # Set member token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.member_token}')
        
        # Try to access applications list
        response = self.client.get('/api/applications/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to access contact messages list
        response = self.client.get('/api/contacts/list/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to access auth logs
        response = self.client.get('/api/auth/logs')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_authenticated_users_can_access_me_endpoint(self):
        """Test that any authenticated user can access /api/auth/me"""
        
        # Admin user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'admin@test.com')
        self.assertEqual(response.data['role'], '1')
        
        # Member user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.member_token}')
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'member@test.com')
        self.assertEqual(response.data['role'], '2')
    
    def test_invalid_token_returns_401(self):
        """Test that invalid tokens return 401 Unauthorized"""
        
        # Set invalid token
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_here')
        
        # Try to access protected endpoint
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_expired_token_returns_401(self):
        """Test that expired tokens return 401 Unauthorized"""
        
        # Create an expired token (this is a simplified test)
        # In real scenario, you'd need to mock time or wait for expiration
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {expired_token}')
        
        # Try to access protected endpoint
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_missing_authorization_header_returns_401(self):
        """Test that missing Authorization header returns 401"""
        
        # Clear credentials
        self.client.credentials()
        
        # Try to access protected endpoint
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_malformed_authorization_header_returns_401(self):
        """Test that malformed Authorization header returns 401"""
        
        # Set malformed header (missing 'Bearer' prefix)
        self.client.credentials(HTTP_AUTHORIZATION=self.admin_token)
        
        # Try to access protected endpoint
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_logout_blacklists_token(self):
        """Test that logout properly blacklists the refresh token"""
        
        # Generate refresh token
        refresh = RefreshToken.for_user(self.admin_user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        # Set access token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Logout (with proper JSON format)
        response = self.client.post('/api/auth/logout', 
            {'refresh_token': refresh_token},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Try to use the refresh token (should fail)
        response = self.client.post('/api/auth/refresh', 
            {'refresh_token': refresh_token},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_error_response_format(self):
        """Test that error responses follow the standard format"""
        
        # Try to access protected endpoint without auth
        response = self.client.get('/api/applications/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('success', response.data)
        self.assertFalse(response.data['success'])
        self.assertIn('error', response.data)
        self.assertIn('code', response.data['error'])
        self.assertIn('message', response.data['error'])
    
    def test_security_headers_present(self):
        """Test that security headers are present in responses"""
        
        response = self.client.get('/')
        
        # Check for security headers
        self.assertIn('X-Content-Type-Options', response)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        
        self.assertIn('X-Frame-Options', response)
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        
        self.assertIn('X-XSS-Protection', response)
        self.assertEqual(response['X-XSS-Protection'], '1; mode=block')


@pytest.mark.django_db
class TestPermissionClasses:
    """
    Test custom permission classes
    """
    
    def test_is_admin_permission(self):
        """Test IsAdmin permission class"""
        from authentication.permissions import IsAdmin
        from rest_framework.test import APIRequestFactory
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        factory = APIRequestFactory()
        permission = IsAdmin()
        
        # Create admin user
        admin = User.objects.create_user(
            email='admin@test.com',
            password='pass',
            role='1'
        )
        
        # Create member user
        member = User.objects.create_user(
            email='member@test.com',
            password='pass',
            role='2'
        )
        
        # Test with admin
        request = factory.get('/')
        request.user = admin
        assert permission.has_permission(request, None) is True
        
        # Test with member
        request = factory.get('/')
        request.user = member
        assert permission.has_permission(request, None) is False
    
    def test_is_member_permission(self):
        """Test IsMember permission class"""
        from authentication.permissions import IsMember
        from rest_framework.test import APIRequestFactory
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        factory = APIRequestFactory()
        permission = IsMember()
        
        # Create member user
        member = User.objects.create_user(
            email='member@test.com',
            password='pass',
            role='2'
        )
        
        # Create admin user
        admin = User.objects.create_user(
            email='admin@test.com',
            password='pass',
            role='1'
        )
        
        # Test with member
        request = factory.get('/')
        request.user = member
        assert permission.has_permission(request, None) is True
        
        # Test with admin
        request = factory.get('/')
        request.user = admin
        assert permission.has_permission(request, None) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
