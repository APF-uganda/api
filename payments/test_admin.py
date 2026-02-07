"""
Unit tests for payment admin views.

Tests cover:
- List display with key fields
- Filters (status, provider, date range)
- Search functionality
- Payment statistics display
- Detail view with formatted data
- Phone number masking
"""
import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .admin import PaymentAdmin, DateRangeFilter
from .models import Payment, PaymentConfig

User = get_user_model()


class MockRequest:
    """Mock request object for admin tests."""
    def __init__(self, user=None):
        self.user = user


class PaymentAdminListDisplayTest(TestCase):
    """Test admin list display functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = PaymentAdmin(Payment, self.site)
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create superuser for admin access
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create test payment
        self.payment = Payment.objects.create(
            transaction_reference='TEST-REF-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            currency='UGX',
            provider=Payment.PROVIDER_MTN,
            status=Payment.STATUS_COMPLETED
        )
    
    def test_list_display_fields(self):
        """Test that list display includes all required fields."""
        expected_fields = [
            'transaction_reference',
            'user',
            'masked_phone',
            'amount',
            'currency',
            'provider',
            'colored_status',
            'created_at',
        ]
        
        self.assertEqual(self.admin.list_display, expected_fields)
    
    def test_masked_phone_display(self):
        """Test that phone numbers are masked in list display."""
        masked = self.admin.masked_phone(self.payment)
        
        # Should show format: 256****3456
        self.assertIn('256', masked)
        self.assertIn('3456', masked)
        self.assertIn('****', masked)
        self.assertNotIn('708123', masked)
    
    def test_colored_status_display(self):
        """Test that status is displayed with color coding."""
        # Test completed status (green)
        self.payment.status = Payment.STATUS_COMPLETED
        html = self.admin.colored_status(self.payment)
        self.assertIn('#28a745', html)  # Green color
        self.assertIn('Completed', html)
        
        # Test failed status (red)
        self.payment.status = Payment.STATUS_FAILED
        html = self.admin.colored_status(self.payment)
        self.assertIn('#dc3545', html)  # Red color
        self.assertIn('Failed', html)
        
        # Test pending status (yellow)
        self.payment.status = Payment.STATUS_PENDING
        html = self.admin.colored_status(self.payment)
        self.assertIn('#ffc107', html)  # Yellow color
        self.assertIn('Pending', html)


class PaymentAdminFiltersTest(TestCase):
    """Test admin filter functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = PaymentAdmin(Payment, self.site)
        self.factory = RequestFactory()
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
    
    def test_list_filters_configured(self):
        """Test that all required filters are configured."""
        expected_filters = [
            'status',
            'provider',
            DateRangeFilter,
            'currency',
        ]
        
        self.assertEqual(self.admin.list_filter, expected_filters)
    
    def test_date_range_filter_today(self):
        """Test date range filter for today."""
        # Create payment today
        today_payment = Payment.objects.create(
            transaction_reference='TODAY-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN
        )
        
        # Create payment yesterday
        yesterday = timezone.now() - timedelta(days=1)
        yesterday_payment = Payment.objects.create(
            transaction_reference='YESTERDAY-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN
        )
        yesterday_payment.created_at = yesterday
        yesterday_payment.save()
        
        # Test filter
        request = self.factory.get('/admin/payments/payment/', {'date_range': 'today'})
        request.user = self.admin_user
        
        filter_instance = DateRangeFilter(
            request,
            {'date_range': 'today'},
            Payment,
            self.admin
        )
        
        queryset = Payment.objects.all()
        filtered = filter_instance.queryset(request, queryset)
        
        self.assertIn(today_payment, filtered)
        self.assertNotIn(yesterday_payment, filtered)
    
    def test_date_range_filter_week(self):
        """Test date range filter for past 7 days."""
        # Create payment within week
        recent_payment = Payment.objects.create(
            transaction_reference='RECENT-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN
        )
        
        # Create payment older than week
        old_date = timezone.now() - timedelta(days=10)
        old_payment = Payment.objects.create(
            transaction_reference='OLD-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN
        )
        old_payment.created_at = old_date
        old_payment.save()
        
        # Test filter
        request = self.factory.get('/admin/payments/payment/', {'date_range': 'week'})
        request.user = self.admin_user
        
        filter_instance = DateRangeFilter(
            request,
            {'date_range': 'week'},
            Payment,
            self.admin
        )
        
        queryset = Payment.objects.all()
        filtered = filter_instance.queryset(request, queryset)
        
        self.assertIn(recent_payment, filtered)
        self.assertNotIn(old_payment, filtered)


class PaymentAdminSearchTest(TestCase):
    """Test admin search functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = PaymentAdmin(Payment, self.site)
        
        self.user = User.objects.create_user(
            email='john.doe@example.com',
            password='testpass123'
        )
        
        self.payment = Payment.objects.create(
            transaction_reference='SEARCH-TEST-001',
            provider_transaction_id='MTN-TX-12345',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN
        )
    
    def test_search_fields_configured(self):
        """Test that search fields are properly configured."""
        expected_fields = [
            'transaction_reference',
            'provider_transaction_id',
            'user__email',
        ]
        
        self.assertEqual(self.admin.search_fields, expected_fields)
    
    def test_search_by_transaction_reference(self):
        """Test searching by transaction reference."""
        queryset = Payment.objects.all()
        search_term = 'SEARCH-TEST'
        
        # Simulate search
        filtered = queryset.filter(transaction_reference__icontains=search_term)
        
        self.assertIn(self.payment, filtered)
        self.assertEqual(filtered.count(), 1)
    
    def test_search_by_user_email(self):
        """Test searching by user email."""
        queryset = Payment.objects.all()
        search_term = 'john.doe'
        
        # Simulate search
        filtered = queryset.filter(user__email__icontains=search_term)
        
        self.assertIn(self.payment, filtered)
        self.assertEqual(filtered.count(), 1)


class PaymentAdminStatisticsTest(TestCase):
    """Test payment statistics display in admin."""
    
    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = PaymentAdmin(Payment, self.site)
        self.factory = RequestFactory()
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create test payments with different statuses and providers
        # MTN completed
        Payment.objects.create(
            transaction_reference='MTN-COMPLETE-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN,
            status=Payment.STATUS_COMPLETED
        )
        
        # MTN failed
        Payment.objects.create(
            transaction_reference='MTN-FAILED-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN,
            status=Payment.STATUS_FAILED
        )
        
        # Airtel completed
        Payment.objects.create(
            transaction_reference='AIRTEL-COMPLETE-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('75000.00'),
            provider=Payment.PROVIDER_AIRTEL,
            status=Payment.STATUS_COMPLETED
        )
        
        # Pending payment
        Payment.objects.create(
            transaction_reference='PENDING-001',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            provider=Payment.PROVIDER_MTN,
            status=Payment.STATUS_PENDING
        )
    
    def test_total_revenue_calculation(self):
        """Test that total revenue is calculated correctly."""
        request = self.factory.get('/admin/payments/payment/')
        request.user = self.admin_user
        
        response = self.admin.changelist_view(request)
        stats = response.context_data['payment_statistics']
        
        # Only completed payments: 50000 + 75000 = 125000
        self.assertEqual(stats['total_revenue'], Decimal('125000.00'))
    
    def test_overall_success_rate_calculation(self):
        """Test that overall success rate is calculated correctly."""
        request = self.factory.get('/admin/payments/payment/')
        request.user = self.admin_user
        
        response = self.admin.changelist_view(request)
        stats = response.context_data['payment_statistics']
        
        # 2 completed out of 3 attempts (2 completed + 1 failed) = 66.67%
        self.assertAlmostEqual(stats['overall_success_rate'], 66.67, places=2)
    
    def test_mtn_provider_statistics(self):
        """Test MTN provider statistics calculation."""
        request = self.factory.get('/admin/payments/payment/')
        request.user = self.admin_user
        
        response = self.admin.changelist_view(request)
        mtn_stats = response.context_data['payment_statistics']['mtn_stats']
        
        self.assertEqual(mtn_stats['total'], 3)  # 1 completed + 1 failed + 1 pending
        self.assertEqual(mtn_stats['completed'], 1)
        self.assertEqual(mtn_stats['failed'], 1)
        self.assertEqual(mtn_stats['success_rate'], 50.0)  # 1 out of 2 attempts
        self.assertEqual(mtn_stats['revenue'], Decimal('50000.00'))
    
    def test_airtel_provider_statistics(self):
        """Test Airtel provider statistics calculation."""
        request = self.factory.get('/admin/payments/payment/')
        request.user = self.admin_user
        
        response = self.admin.changelist_view(request)
        airtel_stats = response.context_data['payment_statistics']['airtel_stats']
        
        self.assertEqual(airtel_stats['total'], 1)
        self.assertEqual(airtel_stats['completed'], 1)
        self.assertEqual(airtel_stats['failed'], 0)
        self.assertEqual(airtel_stats['success_rate'], 100.0)
        self.assertEqual(airtel_stats['revenue'], Decimal('75000.00'))
    
    def test_status_breakdown(self):
        """Test payment status breakdown."""
        request = self.factory.get('/admin/payments/payment/')
        request.user = self.admin_user
        
        response = self.admin.changelist_view(request)
        breakdown = response.context_data['payment_statistics']['status_breakdown']
        
        self.assertEqual(breakdown['pending'], 1)
        self.assertEqual(breakdown['processing'], 0)
        self.assertEqual(breakdown['completed'], 2)
        self.assertEqual(breakdown['failed'], 1)
        self.assertEqual(breakdown['timeout'], 0)
        self.assertEqual(breakdown['cancelled'], 0)


class PaymentAdminDetailViewTest(TestCase):
    """Test payment detail view in admin."""
    
    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = PaymentAdmin(Payment, self.site)
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.payment = Payment.objects.create(
            transaction_reference='DETAIL-TEST-001',
            provider_transaction_id='MTN-TX-12345',
            user=self.user,
            phone_number='256708123456',
            amount=Decimal('50000.00'),
            currency='UGX',
            provider=Payment.PROVIDER_MTN,
            status=Payment.STATUS_COMPLETED,
            provider_response={'status': 'SUCCESSFUL', 'message': 'Payment completed'}
        )
    
    def test_readonly_fields_configured(self):
        """Test that all fields are readonly in detail view."""
        # All fields should be readonly since we don't allow editing
        self.assertIn('transaction_reference', self.admin.readonly_fields)
        self.assertIn('amount', self.admin.readonly_fields)
        self.assertIn('status', self.admin.readonly_fields)
        self.assertIn('masked_phone', self.admin.readonly_fields)
    
    def test_formatted_provider_response(self):
        """Test that provider response is formatted as JSON."""
        formatted = self.admin.formatted_provider_response(self.payment)
        
        # Should contain formatted JSON
        self.assertIn('<pre', formatted)
        self.assertIn('status', formatted)
        self.assertIn('SUCCESSFUL', formatted)
    
    def test_formatted_provider_response_empty(self):
        """Test formatted response when provider_response is None."""
        self.payment.provider_response = None
        formatted = self.admin.formatted_provider_response(self.payment)
        
        self.assertEqual(formatted, '-')
    
    def test_fieldsets_organization(self):
        """Test that fieldsets are properly organized."""
        fieldsets = self.admin.fieldsets
        
        # Check that we have all expected sections
        section_titles = [fs[0] for fs in fieldsets]
        self.assertIn('Transaction Information', section_titles)
        self.assertIn('User Information', section_titles)
        self.assertIn('Payment Details', section_titles)
        self.assertIn('Status & Errors', section_titles)
        self.assertIn('Timestamps', section_titles)
        self.assertIn('Audit Information', section_titles)


class PaymentAdminPermissionsTest(TestCase):
    """Test admin permissions."""
    
    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = PaymentAdmin(Payment, self.site)
        self.factory = RequestFactory()
        
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.request = MockRequest(user=self.admin_user)
    
    def test_no_add_permission(self):
        """Test that adding payments through admin is disabled."""
        has_permission = self.admin.has_add_permission(self.request)
        self.assertFalse(has_permission)
    
    def test_no_delete_permission(self):
        """Test that deleting payments through admin is disabled."""
        has_permission = self.admin.has_delete_permission(self.request)
        self.assertFalse(has_permission)


class PaymentConfigAdminTest(TestCase):
    """Test PaymentConfig admin interface."""
    
    def setUp(self):
        """Set up test data."""
        from .admin import PaymentConfigAdmin
        
        self.site = AdminSite()
        self.admin = PaymentConfigAdmin(PaymentConfig, self.site)
        
        # Get or create config to avoid duplicate key error
        self.config, created = PaymentConfig.objects.get_or_create(
            key='membership_fee_ugx',
            defaults={
                'value': '50000',
                'description': 'APF membership fee in UGX'
            }
        )
    
    def test_list_display_fields(self):
        """Test that list display includes all required fields."""
        expected_fields = ['key', 'value', 'description', 'updated_at']
        self.assertEqual(self.admin.list_display, expected_fields)
    
    def test_search_fields_configured(self):
        """Test that search fields are configured."""
        expected_fields = ['key', 'description']
        self.assertEqual(self.admin.search_fields, expected_fields)
