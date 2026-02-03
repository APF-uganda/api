"""
Script to create default report templates
Run this after setting up the database to populate report templates
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from reports.models import ReportTemplate
from authentication.models import User

def create_default_templates():
    """Create default system report templates"""
    
    # Get or create system admin user
    admin_user = User.objects.filter(role='1').first()
    if not admin_user:
        print("No admin user found. Please create an admin user first.")
        return
    
    print(f"Using admin user: {admin_user.email}")
    
    # Define default templates
    templates_data = [
        {
            'name': 'Membership Report',
            'report_type': 'membership',
            'description': 'Overview of all members, categories, and status. Track member growth, retention, and demographics.',
            'output_format': 'pdf',
            'fields_to_include': ['member_name', 'email', 'membership_type', 'join_date', 'status'],
            'filters': {'status': 'active'},
            'chart_configs': {
                'charts': ['growth_trend', 'status_distribution'],
                'period': '12m'
            },
            'is_system_template': True
        },
        {
            'name': 'Applications Report',
            'report_type': 'applications',
            'description': 'Complete overview of membership applications with status breakdown and processing timelines.',
            'output_format': 'excel',
            'fields_to_include': ['applicant_name', 'email', 'status', 'submission_date', 'review_date'],
            'filters': {},
            'chart_configs': {
                'charts': ['status_breakdown', 'weekly_trends'],
                'period': '30d'
            },
            'is_system_template': True
        },
        {
            'name': 'Financial Report',
            'report_type': 'financial',
            'description': 'Revenue, payments, and outstanding dues analysis. Financial performance and trends.',
            'output_format': 'pdf',
            'fields_to_include': ['transaction_date', 'amount', 'type', 'member', 'status'],
            'filters': {'period': 'current_quarter'},
            'chart_configs': {
                'charts': ['revenue_trend', 'payment_methods'],
                'period': '3m'
            },
            'is_system_template': True
        },
        {
            'name': 'Events Report',
            'report_type': 'events',
            'description': 'Event attendants, engagement metrics, and participation analysis across all events.',
            'output_format': 'pdf',
            'fields_to_include': ['event_name', 'date', 'attendees', 'location', 'status'],
            'filters': {'status': 'completed'},
            'chart_configs': {
                'charts': ['attendance_trend', 'event_participation'],
                'period': '6m'
            },
            'is_system_template': True
        },
        {
            'name': 'Compliance Report',
            'report_type': 'compliance',
            'description': 'CPD tracking and certificate verification status. Compliance monitoring and audit trails.',
            'output_format': 'pdf',
            'fields_to_include': ['member_name', 'cpd_credits', 'certification_status', 'expiry_date'],
            'filters': {'compliance_status': 'all'},
            'chart_configs': {
                'charts': ['compliance_rate', 'expiring_certifications'],
                'period': '12m'
            },
            'is_system_template': True
        },
        {
            'name': 'Growth Analysis Report',
            'report_type': 'growth',
            'description': 'New member acquisition and retention trends. Growth analysis and forecasting.',
            'output_format': 'excel',
            'fields_to_include': ['month', 'new_members', 'churned_members', 'net_growth'],
            'filters': {'period': 'last_12_months'},
            'chart_configs': {
                'charts': ['growth_trend', 'acquisition_channels', 'retention_rate'],
                'period': '12m'
            },
            'is_system_template': True
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for template_data in templates_data:
        # Check if template already exists
        existing = ReportTemplate.objects.filter(
            report_type=template_data['report_type'],
            is_system_template=True
        ).first()
        
        if existing:
            # Update existing template
            for key, value in template_data.items():
                if key != 'created_by':
                    setattr(existing, key, value)
            existing.save()
            updated_count += 1
            print(f"✓ Updated: {template_data['name']}")
        else:
            # Create new template
            ReportTemplate.objects.create(
                **template_data,
                created_by=admin_user
            )
            created_count += 1
            print(f"✓ Created: {template_data['name']}")
    
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Created: {created_count} templates")
    print(f"  Updated: {updated_count} templates")
    print(f"  Total: {created_count + updated_count} templates")
    print(f"{'='*50}\n")

if __name__ == '__main__':
    print("Creating default report templates...\n")
    try:
        create_default_templates()
        print("\n✅ Successfully created/updated report templates!")
    except Exception as e:
        print(f"\n❌ Error creating templates: {str(e)}")
        import traceback
        traceback.print_exc()
