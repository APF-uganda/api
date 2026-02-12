from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from Documents.models import MemberDocument
from .models import SuspendedMember, ProcessedDocument, MembershipStatus, DocumentStatus
from authentication.models import User, UserRole
from rest_framework_simplejwt.tokens import AccessToken


User = get_user_model()


class AdminManagementTestCase(TestCase):
    """
    Test suite for admin management endpoints
    """
    
    def setUp(self):
        """
        Set up test data
        """
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='adminpass123',
            role=UserRole.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        
        # Create regular member user
        self.member_user = User.objects.create_user(
            email='member@test.com',
            password='memberpass123',
            role=UserRole.MEMBER,
            first_name='Test',
            last_name='Member',
            phone_number='+256123456789'
        )
        
        # Create another member user for testing
        self.another_member = User.objects.create_user(
            email='another@test.com',
            password='memberpass123',
            role=UserRole.MEMBER,
            first_name='Another',
            last_name='Member'
        )
        
        # Create a test document for the member
        self.member_document = MemberDocument.objects.create(
            user=self.member_user,
            file_name='test_document.pdf',
            file_type='pdf',
            file_size=1024,
            document_type='license',
            status=DocumentStatus.PENDING
        )
        
        # Create client
        self.client = Client()
        
        # Login admin user and get JWT token
        login_response = self.client.post('/api/v1/auth/login/', {
            'email': 'admin@test.com',
            'password': 'adminpass123'
        })
        if login_response.status_code == 200:
            self.admin_token = login_response.json()['access']
        else:
            # Fallback - manually create token for testing
            token = AccessToken.for_user(self.admin_user)
            self.admin_token = str(token)
        
        # Login member user to get member token
        member_login_response = self.client.post('/api/v1/auth/login/', {
            'email': 'member@test.com',
            'password': 'memberpass123'
        })
        if member_login_response.status_code == 200:
            self.member_token = member_login_response.json()['access']
        else:
            token = AccessToken.for_user(self.member_user)
            self.member_token = str(token)
    
    def get_auth_headers(self, token):
        """
        Helper method to create authorization headers
        """
        return {
            'HTTP_AUTHORIZATION': f'Bearer {token}',
            'content_type': 'application/json'
        }
    
    def test_get_all_members_as_admin(self):
        """
        Test that admin can get all members
        """
        headers = self.get_auth_headers(self.admin_token)
        response = self.client.get(reverse('admin-members-list'), **headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.json())
        self.assertIn('results', response.json())
        
        # Check that member is in the results
        results = response.json()['results']
        member_emails = [member['email'] for member in results]
        self.assertIn('member@test.com', member_emails)
        self.assertIn('another@test.com', member_emails)
    
    def test_get_members_with_status_filter(self):
        """
        Test filtering members by status
        """
        # Suspend one member first
        self.client.patch(
            reverse('admin-member-suspend', kwargs={'member_id': self.member_user.id}),
            data={'reason': 'Test suspension'},
            **self.get_auth_headers(self.admin_token)
        )
        
        headers = self.get_auth_headers(self.admin_token)
        response = self.client.get(
            f"{reverse('admin-members-list')}?status=SUSPENDED",
            **headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()['results']
        # Should only contain suspended members
        self.assertGreater(len(results), 0)
    
    def test_get_members_with_search_filter(self):
        """
        Test searching members by name or email
        """
        headers = self.get_auth_headers(self.admin_token)
        response = self.client.get(
            f"{reverse('admin-members-list')}?search=Test",
            **headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()['results']
        # Should contain members with 'Test' in name
        self.assertGreater(len(results), 0)
    
    def test_suspend_member_as_admin(self):
        """
        Test that admin can suspend a member
        """
        response = self.client.patch(
            reverse('admin-member-suspend', kwargs={'member_id': self.member_user.id}),
            data={'reason': 'Annual subscription not paid'},
            **self.get_auth_headers(self.admin_token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.json())
        self.assertEqual(response.json()['message'], 'Member suspended successfully')
        
        # Verify member is suspended in DB
        self.member_user.refresh_from_db()
        suspension_record = SuspendedMember.objects.get(user=self.member_user)
        self.assertIsNotNone(suspension_record)
        self.assertEqual(suspension_record.suspension_reason, 'Annual subscription not paid')
    
    def test_reactivate_member_as_admin(self):
        """
        Test that admin can reactivate a suspended member
        """
        # First suspend the member
        self.client.patch(
            reverse('admin-member-suspend', kwargs={'member_id': self.member_user.id}),
            data={'reason': 'Annual subscription not paid'},
            **self.get_auth_headers(self.admin_token)
        )
        
        # Then reactivate the member
        response = self.client.patch(
            reverse('admin-member-reactivate', kwargs={'member_id': self.member_user.id}),
            **self.get_auth_headers(self.admin_token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.json())
        self.assertEqual(response.json()['message'], 'Member reactivated successfully')
    
    def test_get_pending_documents_as_admin(self):
        """
        Test that admin can get pending documents
        """
        response = self.client.get(
            reverse('admin-pending-documents'),
            **self.get_auth_headers(self.admin_token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.json())
        self.assertIn('results', response.json())
        
        # Check that our test document is in the results
        results = response.json()['results']
        document_ids = [doc['id'] for doc in results]
        self.assertIn(self.member_document.id, document_ids)
    
    def test_approve_document_as_admin(self):
        """
        Test that admin can approve a document
        """
        response = self.client.patch(
            reverse('admin-document-approve', kwargs={'document_id': self.member_document.id}),
            **self.get_auth_headers(self.admin_token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.json())
        self.assertEqual(response.json()['message'], 'Document approved successfully')
        
        # Verify document is approved in DB
        self.member_document.refresh_from_db()
        self.assertEqual(self.member_document.status, DocumentStatus.APPROVED)
        
        # Verify processed record is created
        processed_record = ProcessedDocument.objects.get(document=self.member_document)
        self.assertEqual(processed_record.status, DocumentStatus.APPROVED)
        self.assertIsNotNone(processed_record.approved_at)
        self.assertEqual(processed_record.approved_by, self.admin_user)
    
    def test_reject_document_as_admin(self):
        """
        Test that admin can reject a document
        """
        response = self.client.patch(
            reverse('admin-document-reject', kwargs={'document_id': self.member_document.id}),
            data={'reason': 'Document is invalid'},
            **self.get_auth_headers(self.admin_token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.json())
        self.assertEqual(response.json()['message'], 'Document rejected successfully')
        
        # Verify document is rejected in DB
        self.member_document.refresh_from_db()
        self.assertEqual(self.member_document.status, DocumentStatus.REJECTED)
        self.assertEqual(self.member_document.admin_feedback, 'Document is invalid')
        
        # Verify processed record is created
        processed_record = ProcessedDocument.objects.get(document=self.member_document)
        self.assertEqual(processed_record.status, DocumentStatus.REJECTED)
        self.assertEqual(processed_record.rejection_reason, 'Document is invalid')
        self.assertIsNotNone(processed_record.rejected_at)
    
    def test_non_admin_cannot_access_endpoints(self):
        """
        Test that non-admin users cannot access admin endpoints
        """
        # Test with member token
        headers = self.get_auth_headers(self.member_token)
        response = self.client.get(reverse('admin-members-list'), **headers)
        
        # Should return 403 Forbidden or 400 Bad Request depending on permission handling
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])
    
    def test_admin_member_not_found(self):
        """
        Test that trying to suspend a non-existent member returns error
        """
        response = self.client.patch(
            reverse('admin-member-suspend', kwargs={'member_id': 99999}),
            data={'reason': 'Test suspension'},
            **self.get_auth_headers(self.admin_token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_admin_document_not_found(self):
        """
        Test that trying to approve a non-existent document returns error
        """
        response = self.client.patch(
            reverse('admin-document-approve', kwargs={'document_id': 99999}),
            **self.get_auth_headers(self.admin_token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())


class AdminManagementPermissionsTestCase(TestCase):
    """
    Test suite for admin management permissions
    """
    
    def setUp(self):
        """
        Set up test data
        """
        # Create regular member user (non-admin)
        self.member_user = User.objects.create_user(
            email='member@test.com',
            password='memberpass123',
            role=UserRole.MEMBER
        )
        
        # Create client
        self.client = Client()
        
        # Login member user
        login_response = self.client.post('/api/v1/auth/login/', {
            'email': 'member@test.com',
            'password': 'memberpass123'
        })
        if login_response.status_code == 200:
            self.member_token = login_response.json()['access']
        else:
            token = AccessToken.for_user(self.member_user)
            self.member_token = str(token)
    
    def get_auth_headers(self, token):
        """
        Helper method to create authorization headers
        """
        return {
            'HTTP_AUTHORIZATION': f'Bearer {token}',
            'content_type': 'application/json'
        }
    
    def test_member_cannot_access_member_list(self):
        """
        Test that regular members cannot access member list
        """
        headers = self.get_auth_headers(self.member_token)
        response = self.client.get(reverse('admin-members-list'), **headers)
        
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])
    
    def test_member_cannot_suspend_member(self):
        """
        Test that regular members cannot suspend members
        """
        # Create another member to try to suspend
        other_member = User.objects.create_user(
            email='other@test.com',
            password='otherpass123',
            role=UserRole.MEMBER
        )
        
        response = self.client.patch(
            reverse('admin-member-suspend', kwargs={'member_id': other_member.id}),
            data={'reason': 'Test suspension'},
            **self.get_auth_headers(self.member_token)
        )
        
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])
    
    def test_unauthenticated_user_cannot_access_endpoints(self):
        """
        Test that unauthenticated users cannot access admin endpoints
        """
        response = self.client.get(reverse('admin-members-list'))
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])