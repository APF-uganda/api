"""
Unit tests for Application-to-User migration functionality
Tests User creation on Application approval, duplicate prevention, password hashing, and linking
"""
import pytest
from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase
from applications.models import Application
from applications.serializers import ApplicationSerializer
from authentication.models import User, UserRole
from authentication.services import UserCreationService


@pytest.mark.django_db
class TestApplicationUserMigration(TestCase):
    """Test suite for Application-to-User migration"""
    
    def setUp(self):
        """Set up test data"""
        self.application_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password_hash': 'plainpassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'date_of_birth': '1990-01-01',
            'phone_number': '256700000000',
            'address': '123 Test St',
            'payment_method': 'mtn',
            'payment_phone': '256700000000',
            'payment_status': 'success',
            'status': 'pending'
        }
    
    def test_user_creation_on_application_approval(self):
        """
        Test that User account is automatically created when Application is approved
        Requirements: 12.1
        """
        # Create a pending application
        application = Application.objects.create(**self.application_data)
        
        # Verify no user exists yet
        self.assertIsNone(application.user)
        self.assertEqual(User.objects.filter(email=application.email).count(), 0)
        
        # Approve the application
        application.status = 'approved'
        application.save()
        
        # Refresh from database
        application.refresh_from_db()
        
        # Verify user was created and linked
        self.assertIsNotNone(application.user)
        self.assertEqual(application.user.email, application.email)
        self.assertEqual(application.user.role, UserRole.MEMBER)
        self.assertTrue(application.user.is_active)
    
    def test_duplicate_user_prevention(self):
        """
        Test that duplicate User creation is prevented if User already exists
        Requirements: 12.5
        """
        # Create a user first
        existing_user = User.objects.create_user(
            email=self.application_data['email'],
            password='existingpassword'
        )
        
        # Create an application with the same email
        application = Application.objects.create(**self.application_data)
        
        # Try to create user from application
        user, error = UserCreationService.create_user_from_application(application)
        
        # Verify user creation failed
        self.assertIsNone(user)
        self.assertIsNotNone(error)
        self.assertIn("already exists", error.lower())
        
        # Verify only one user exists
        self.assertEqual(User.objects.filter(email=self.application_data['email']).count(), 1)
    
    def test_password_hashing_in_serializer(self):
        """
        Test that ApplicationSerializer hashes passwords before saving
        Requirements: 12.6
        """
        # Create application using serializer
        serializer = ApplicationSerializer(data=self.application_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        application = serializer.save()
        
        # Verify password was hashed
        self.assertNotEqual(application.password_hash, 'plainpassword123')
        self.assertTrue(check_password('plainpassword123', application.password_hash))
    
    def test_user_application_linking(self):
        """
        Test that User is properly linked to Application via foreign key
        Requirements: 12.4
        """
        # Create application with hashed password
        self.application_data['password_hash'] = make_password('plainpassword123')
        application = Application.objects.create(**self.application_data)
        
        # Create user from application
        user, error = UserCreationService.create_user_from_application(application)
        
        # Verify linking
        self.assertIsNone(error)
        self.assertIsNotNone(user)
        
        # Refresh application from database
        application.refresh_from_db()
        
        # Verify foreign key relationship
        self.assertEqual(application.user, user)
        self.assertEqual(application.user.id, user.id)
        
        # Verify reverse relationship
        self.assertIn(application, user.applications.all())
    
    def test_user_role_set_to_member(self):
        """
        Test that created User has role set to 2 (member)
        Requirements: 12.3
        """
        # Create application with hashed password
        self.application_data['password_hash'] = make_password('plainpassword123')
        application = Application.objects.create(**self.application_data)
        
        # Create user from application
        user, error = UserCreationService.create_user_from_application(application)
        
        # Verify role is set to member
        self.assertIsNone(error)
        self.assertEqual(user.role, UserRole.MEMBER)
        self.assertEqual(user.role, '2')
    
    def test_password_hash_copied_from_application(self):
        """
        Test that password_hash is copied from Application to User
        Requirements: 12.2
        """
        # Create application with pre-hashed password
        hashed_password = make_password('testpassword123')
        self.application_data['password_hash'] = hashed_password
        application = Application.objects.create(**self.application_data)
        
        # Create user from application
        user, error = UserCreationService.create_user_from_application(application)
        
        # Verify password hash was copied
        self.assertIsNone(error)
        self.assertEqual(user.password, hashed_password)
        self.assertTrue(check_password('testpassword123', user.password))
    
    def test_signal_handler_creates_user_on_approval(self):
        """
        Test that signal handler automatically creates user when status changes to approved
        Requirements: 12.1
        """
        # Create application using serializer (which hashes password)
        serializer = ApplicationSerializer(data=self.application_data)
        self.assertTrue(serializer.is_valid())
        application = serializer.save()
        
        # Verify no user exists yet
        self.assertIsNone(application.user)
        
        # Change status to approved (triggers signal)
        application.status = 'approved'
        application.save()
        
        # Refresh from database
        application.refresh_from_db()
        
        # Verify user was created by signal
        self.assertIsNotNone(application.user)
        self.assertEqual(application.user.email, application.email)
        self.assertEqual(application.user.role, UserRole.MEMBER)
    
    def test_no_user_creation_for_rejected_application(self):
        """
        Test that User is not created when Application is rejected
        """
        # Create a pending application
        application = Application.objects.create(**self.application_data)
        
        # Reject the application
        application.status = 'rejected'
        application.save()
        
        # Refresh from database
        application.refresh_from_db()
        
        # Verify no user was created
        self.assertIsNone(application.user)
        self.assertEqual(User.objects.filter(email=application.email).count(), 0)
    
    def test_user_creation_service_error_handling(self):
        """
        Test that UserCreationService handles errors gracefully
        """
        # Create application without required fields (should cause error)
        invalid_application = Application(
            email='invalid@example.com',
            password_hash='',  # Empty password
            status='approved'
        )
        
        # Try to create user (should handle error)
        user, error = UserCreationService.create_user_from_application(invalid_application)
        
        # Verify error was returned
        self.assertIsNone(user)
        self.assertIsNotNone(error)
