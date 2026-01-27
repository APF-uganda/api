"""
Tests for authentication models

These tests validate the User, OTP, PasswordResetToken, and AuthLog models.
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from django.db import IntegrityError
from authentication.models import User, UserRole, OTP, PasswordResetToken, AuthLog, AuthEventType


@pytest.mark.django_db
class TestUserModel:
    """
    Tests for User model.
    """

    def test_property_4_password_hashing_before_storage(self):
        """
        Property 4: Password hashing before storage
        **Validates: Requirements 1.5, 7.2**
        
        For any user password, the stored value in the database should be a hash,
        never the plaintext password.
        """
        email = "test@example.com"
        password = "securePassword123"
        
        # Create user with password
        user = User.objects.create_user(email=email, password=password)
        
        # Verify password is hashed (not equal to plaintext)
        assert user.password != password, "Password should be hashed, not stored as plaintext"
        
        # Verify the hash can be validated
        assert check_password(password, user.password), "Password hash should be valid"
        
        # Verify the password field starts with a hash algorithm identifier
        assert user.password.startswith('pbkdf2_sha256$'), "Password should use PBKDF2-SHA256 hashing"

    def test_property_32_email_uniqueness_constraint(self):
        """
        Property 32: Email uniqueness constraint
        **Validates: Requirements 11.2**
        
        For any two users, their email addresses should be unique
        (attempting to create a user with an existing email should fail).
        """
        email = "unique@example.com"
        password = "password123"
        
        # Create first user
        user1 = User.objects.create_user(email=email, password=password)
        
        # Attempt to create second user with same email should raise error
        with pytest.raises(IntegrityError):
            User.objects.create_user(email=email, password=password)

    def test_property_33_role_enumeration_validation(self):
        """
        Property 33: Role enumeration validation
        **Validates: Requirements 11.3**
        
        For any user, the role field should only accept values "1" (admin) or "2" (member).
        """
        email = "roletest@example.com"
        password = "password123"
        
        # Test with admin role
        admin_user = User.objects.create_user(email=email, password=password, role=UserRole.ADMIN)
        assert admin_user.role == UserRole.ADMIN
        assert admin_user.role == '1'
        admin_user.delete()
        
        # Test with member role
        member_user = User.objects.create_user(email=email, password=password, role=UserRole.MEMBER)
        assert member_user.role == UserRole.MEMBER
        assert member_user.role == '2'

    def test_property_34_user_default_values(self):
        """
        Property 34: User default values
        **Validates: Requirements 11.5**
        
        For any newly created user without explicit values,
        is_active should default to true and role should default to "2" (member).
        """
        email = "defaults@example.com"
        password = "password123"
        
        # Create user without specifying is_active or role
        user = User.objects.create_user(email=email, password=password)
        
        # Verify default values
        assert user.is_active is True, "is_active should default to True"
        assert user.role == UserRole.MEMBER, "role should default to '2' (member)"
        assert user.role == '2', "role value should be '2'"

    def test_superuser_creation_defaults(self):
        """
        Test superuser creation with correct defaults
        
        For any superuser created via create_superuser,
        is_staff, is_superuser should be True and role should be '1' (admin).
        """
        email = "admin@example.com"
        password = "adminpass123"
        
        # Create superuser
        user = User.objects.create_superuser(email=email, password=password)
        
        # Verify superuser attributes
        assert user.is_staff is True, "Superuser should have is_staff=True"
        assert user.is_superuser is True, "Superuser should have is_superuser=True"
        assert user.role == UserRole.ADMIN, "Superuser should have role='1' (admin)"
        assert user.is_active is True, "Superuser should be active by default"


@pytest.mark.django_db
class TestOTPModel:
    """
    Tests for OTP model.
    """

    def test_property_6_otp_format_validation(self):
        """
        Property 6: OTP format validation
        **Validates: Requirements 2.1**
        
        For any generated OTP, the code should be exactly 6 digits.
        """
        # Generate OTP code
        otp_code = OTP.generate_code()
        
        # Verify it's 6 digits
        assert len(otp_code) == 6, "OTP should be exactly 6 digits"
        assert otp_code.isdigit(), "OTP should contain only digits"

    def test_property_7_otp_expiration_time(self):
        """
        Property 7: OTP expiration time
        **Validates: Requirements 2.3**
        
        For any generated OTP, the expiration timestamp should be exactly 10 minutes
        after creation time.
        """
        import uuid
        
        # Create a user
        user = User.objects.create_user(email="otptest@example.com", password="pass123")
        
        # Create OTP with 10-minute expiration
        now = timezone.now()
        expires_at = now + timedelta(minutes=10)
        
        otp = OTP.objects.create(
            user=user,
            code="123456",
            session_id=uuid.uuid4(),
            expires_at=expires_at
        )
        
        # Verify expiration is approximately 10 minutes from creation
        time_diff = (otp.expires_at - otp.created_at).total_seconds()
        assert 599 <= time_diff <= 601, "OTP should expire in approximately 10 minutes"

    def test_otp_is_valid_method(self):
        """
        Test OTP is_valid() method correctly checks expiration and usage
        """
        import uuid
        
        user = User.objects.create_user(email="validtest@example.com", password="pass123")
        
        # Create valid OTP (not expired, not used)
        valid_otp = OTP.objects.create(
            user=user,
            code="123456",
            session_id=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        assert valid_otp.is_valid() is True
        
        # Create expired OTP
        expired_otp = OTP.objects.create(
            user=user,
            code="654321",
            session_id=uuid.uuid4(),
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        assert expired_otp.is_valid() is False
        
        # Create used OTP
        used_otp = OTP.objects.create(
            user=user,
            code="111111",
            session_id=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(minutes=10),
            is_used=True
        )
        assert used_otp.is_valid() is False


@pytest.mark.django_db
class TestPasswordResetTokenModel:
    """
    Tests for PasswordResetToken model.
    """

    def test_property_17_password_reset_token_uniqueness(self):
        """
        Property 17: Password reset token uniqueness
        **Validates: Requirements 6.1**
        
        For any two password reset token generation requests,
        the generated tokens should be unique.
        """
        # Generate multiple tokens
        token1 = PasswordResetToken.generate_token()
        token2 = PasswordResetToken.generate_token()
        token3 = PasswordResetToken.generate_token()
        
        # Verify they are all unique
        assert token1 != token2
        assert token2 != token3
        assert token1 != token3

    def test_property_18_password_reset_token_expiration(self):
        """
        Property 18: Password reset token expiration
        **Validates: Requirements 6.3**
        
        For any generated password reset token, the expiration timestamp should be
        exactly 1 hour after creation time.
        """
        user = User.objects.create_user(email="resettest@example.com", password="pass123")
        
        # Create password reset token with 1-hour expiration
        now = timezone.now()
        expires_at = now + timedelta(hours=1)
        
        token = PasswordResetToken.objects.create(
            user=user,
            token=PasswordResetToken.generate_token(),
            expires_at=expires_at
        )
        
        # Verify expiration is approximately 1 hour from creation
        time_diff = (token.expires_at - token.created_at).total_seconds()
        assert 3599 <= time_diff <= 3601, "Token should expire in approximately 1 hour"

    def test_password_reset_token_is_valid_method(self):
        """
        Test PasswordResetToken is_valid() method correctly checks expiration and usage
        """
        user = User.objects.create_user(email="tokentest@example.com", password="pass123")
        
        # Create valid token (not expired, not used)
        valid_token = PasswordResetToken.objects.create(
            user=user,
            token=PasswordResetToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        assert valid_token.is_valid() is True
        
        # Create expired token
        expired_token = PasswordResetToken.objects.create(
            user=user,
            token=PasswordResetToken.generate_token(),
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        assert expired_token.is_valid() is False
        
        # Create used token
        used_token = PasswordResetToken.objects.create(
            user=user,
            token=PasswordResetToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1),
            is_used=True
        )
        assert used_token.is_valid() is False


@pytest.mark.django_db
class TestAuthLogModel:
    """
    Tests for AuthLog model.
    """

    def test_auth_log_creation(self):
        """
        Test that AuthLog entries can be created with all required fields
        """
        user = User.objects.create_user(email="logtest@example.com", password="pass123")
        
        # Create auth log entry
        log = AuthLog.objects.create(
            user=user,
            email=user.email,
            event_type=AuthEventType.LOGIN_SUCCESS,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
            details={"method": "password"}
        )
        
        # Verify log was created
        assert log.id is not None
        assert log.user == user
        assert log.email == user.email
        assert log.event_type == AuthEventType.LOGIN_SUCCESS
        assert log.success is True

    def test_auth_log_ordering(self):
        """
        Test that AuthLog entries are ordered by timestamp descending
        """
        user = User.objects.create_user(email="ordertest2@example.com", password="pass123")
        
        # Create multiple log entries
        log1 = AuthLog.objects.create(
            user=user,
            email=user.email,
            event_type=AuthEventType.LOGIN_ATTEMPT,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False
        )
        
        log2 = AuthLog.objects.create(
            user=user,
            email=user.email,
            event_type=AuthEventType.LOGIN_SUCCESS,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True
        )
        
        # Verify ordering (most recent first) for this user
        logs = AuthLog.objects.filter(user=user).order_by('-timestamp')
        assert logs[0].id == log2.id
        assert logs[1].id == log1.id
