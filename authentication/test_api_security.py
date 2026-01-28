import pytest
from hypothesis.extra.django import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from hypothesis import given, strategies as st, settings
from datetime import timedelta
from django.utils import timezone
import uuid

from .models import OTP, PasswordResetToken, AuthLog, AuthEventType
from .services import TokenService

User = get_user_model()


@pytest.mark.django_db
class TestAPISecurityProperties(TestCase):
    """Property-based tests for API security requirements"""
    
    def setUp(self):
        self.client = APIClient()
    
    @settings(max_examples=50, deadline=None)
    @given(
        email=st.emails(),
        password=st.text(min_size=8, max_size=50)
    )
    def test_property_2_role_information_in_authentication_response(self, email, password):
        """
        Property 2: Role information in authentication response
        **Validates: Requirements 1.2, 3.1**
        
        For any successfully authenticated user, the authentication response 
        should include the user's role ("1" for admin or "2" for member).
        """
        # Create user with a specific role
        user = User.objects.create_user(
            email=email,
            password=password,
            role='2'  # member
        )
        
        # Create OTP for verification
        session_id = uuid.uuid4()
        otp = OTP.objects.create(
            user=user,
            code='123456',
            session_id=session_id,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Verify OTP
        response = self.client.post('/api/auth/verify-otp', {
            'session_id': str(session_id),
            'otp': '123456',
            'remember_me': False
        }, format='json')
        
        # Assert role is in response
        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'role' in response.data['user']
        assert response.data['user']['role'] in ['1', '2']
    
    @settings(max_examples=50, deadline=None)
    @given(
        email=st.emails(),
        password=st.text(min_size=8, max_size=50)
    )
    def test_property_3_generic_error_messages_for_authentication_failures(self, email, password):
        """
        Property 3: Generic error messages for authentication failures
        **Validates: Requirements 1.3, 1.4, 12.1**
        
        For any authentication failure (invalid password, non-existent email), 
        the error message should be generic and not reveal which specific field 
        was incorrect or whether the account exists.
        """
        # Test with non-existent email
        response = self.client.post('/api/auth/login', {
            'email': email,
            'password': password
        }, format='json')
        
        # Should return generic error message
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            assert response.data['error']['code'] == 'INVALID_CREDENTIALS'
            assert 'Invalid email or password' in response.data['error']['message']
            # Should not reveal specific details like "email doesn't exist" or "wrong password"
            message_lower = response.data['error']['message'].lower()
            assert 'does not exist' not in message_lower
            assert 'not found' not in message_lower
            assert 'incorrect password' not in message_lower
            assert 'wrong password' not in message_lower
    
    @settings(max_examples=50, deadline=None)
    @given(
        email=st.emails(),
        password=st.text(min_size=8, max_size=50)
    )
    def test_property_4_password_hashing_before_storage(self, email, password):
        """
        Property 4: Password hashing before storage
        **Validates: Requirements 1.5, 7.2**
        
        For any user password, the stored value in the database should be a hash, 
        never the plaintext password.
        """
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            role='2'
        )
        
        # Verify password is hashed
        assert user.password != password
        assert len(user.password) > len(password)
        # Django password hashes start with algorithm identifier
        assert user.password.startswith('pbkdf2_sha256$')
    
    @settings(max_examples=50, deadline=None)
    @given(
        email=st.emails(),
        password=st.text(min_size=8, max_size=50)
    )
    def test_property_5_no_plaintext_passwords_in_logs(self, email, password):
        """
        Property 5: No plaintext passwords in logs
        **Validates: Requirements 7.3**
        
        For any authentication event log entry, the log should not contain 
        plaintext passwords.
        """
        # Attempt login (will fail since user doesn't exist)
        self.client.post('/api/auth/login', {
            'email': email,
            'password': password
        }, format='json')
        
        # Check auth logs
        logs = AuthLog.objects.filter(email=email)
        
        for log in logs:
            # Verify password is not in log details
            log_str = str(log.details)
            assert password not in log_str
            # Also check user_agent and other fields
            assert password not in log.user_agent
    
    @settings(max_examples=30, deadline=None)
    @given(
        token_string=st.text(min_size=10, max_size=100, alphabet=st.characters(blacklist_characters='\x00'))
    )
    def test_property_21_invalid_token_rejection(self, token_string):
        """
        Property 21: Invalid token rejection
        **Validates: Requirements 6.6**
        
        For any expired or invalid password reset token, attempting to reset 
        a password should fail with an error response.
        """
        # Try to reset password with invalid token
        response = self.client.post('/api/auth/password-reset-confirm', {
            'token': token_string,
            'new_password': 'newpassword123'
        }, format='json')
        
        # Should reject invalid token
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'INVALID_RESET_TOKEN'
    
    @settings(max_examples=50, deadline=None)
    @given(
        email=st.emails(),
        password=st.text(min_size=8, max_size=50)
    )
    def test_property_35_error_response_security(self, email, password):
        """
        Property 35: Error response security
        **Validates: Requirements 12.1, 12.3, 12.4**
        
        For any error response from the authentication system, the response 
        should not contain sensitive information (passwords, tokens, internal 
        paths, stack traces).
        """
        # Trigger various error responses
        responses = []
        
        # Invalid login
        responses.append(self.client.post('/api/auth/login', {
            'email': email,
            'password': password
        }, format='json'))
        
        # Invalid OTP
        responses.append(self.client.post('/api/auth/verify-otp', {
            'session_id': str(uuid.uuid4()),
            'otp': '123456'
        }, format='json'))
        
        # Invalid refresh token
        responses.append(self.client.post('/api/auth/refresh', {
            'refresh_token': 'invalid_token'
        }, format='json'))
        
        # Check all error responses
        for response in responses:
            if response.status_code >= 400:
                response_str = str(response.data)
                
                # Should not contain sensitive information
                assert password not in response_str
                assert 'Traceback' not in response_str
                assert '/Backend/' not in response_str
                assert 'File "' not in response_str
                
                # Should have proper error structure
                assert 'error' in response.data or 'detail' in response.data
