"""
Membership Renewal Service
Handles sending membership renewal invoices via email
"""
import logging
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from authentication.models import User

logger = logging.getLogger(__name__)


class MembershipRenewalService:
    """Service for managing membership renewals and sending invoice emails"""
    
    # Annual subscription fee - same for all members
    ANNUAL_SUBSCRIPTION_FEE = 150000
    
    @staticmethod
    def get_current_membership_year():
        """
        Get the current membership year period (Apr 1 - Mar 31)
        Returns: tuple (start_year, end_year)
        """
        today = datetime.now()
        current_month = today.month
        current_year = today.year
        
        # If we're in Jan-Mar, membership year started last year
        # If we're in Apr-Dec, membership year started this year
        start_year = current_year - 1 if current_month < 4 else current_year
        end_year = start_year + 1
        
        return start_year, end_year
    
    @staticmethod
    def get_next_membership_year():
        """
        Get the next membership year period
        Returns: tuple (start_year, end_year)
        """
        start_year, end_year = MembershipRenewalService.get_current_membership_year()
        return end_year, end_year + 1
    
    @staticmethod
    def generate_invoice_number():
        """Generate unique invoice number"""
        current_year = datetime.now().year
        timestamp = datetime.now().strftime('%m%d%H%M%S')
        return f"INV-{current_year}-{timestamp}"
    
    @staticmethod
    def calculate_renewal_amount(user):
        """
        Calculate renewal amount for a user
        All members pay the same annual subscription fee
        Returns: dict with amount, previous_balance, discount, total
        """
        base_amount = MembershipRenewalService.ANNUAL_SUBSCRIPTION_FEE
        
        # Check for previous balance (you can implement this based on your payment records)
        previous_balance = 0
        
        # Check for discounts (you can implement discount logic here)
        discount = 0
        
        total = base_amount + previous_balance - discount
        
        return {
            'base_amount': base_amount,
            'previous_balance': previous_balance,
            'discount': discount,
            'total': total
        }
    
    @staticmethod
    def send_renewal_invoice_email(user, letterhead_url=None):
        """
        Send membership renewal invoice email to a user
        
        Args:
            user: User object
            letterhead_url: Optional URL to letterhead image
            
        Returns:
            tuple (success: bool, message: str)
        """
        try:
            # Calculate amounts
            amounts = MembershipRenewalService.calculate_renewal_amount(user)
            
            # Get membership years
            next_start_year, next_end_year = MembershipRenewalService.get_next_membership_year()
            renewal_period = f"Apr {next_start_year} - Mar {next_end_year}"
            
            # Generate invoice details
            invoice_number = MembershipRenewalService.generate_invoice_number()
            invoice_date = datetime.now().strftime('%d/%m/%Y')
            due_date = (datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y')
            
            # Prepare email context
            context = {
                'user': user,
                'invoice_number': invoice_number,
                'invoice_date': invoice_date,
                'due_date': due_date,
                'renewal_period': renewal_period,
                'membership_type': getattr(user, 'membership_category', 'Full Member'),
                'membership_number': getattr(user, 'icpau_registration_number', ''),
                'base_amount': amounts['base_amount'],
                'previous_balance': amounts['previous_balance'],
                'discount': amounts['discount'],
                'total_amount': amounts['total'],
                'letterhead_url': letterhead_url,
            }
            
            # Render email template
            html_message = render_to_string('emails/membership_renewal_invoice.html', context)
            text_message = render_to_string('emails/membership_renewal_invoice.txt', context)
            
            # Create email
            subject = f'Membership Renewal Invoice - {renewal_period}'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            
            email = EmailMessage(
                subject=subject,
                body=text_message,
                from_email=from_email,
                to=recipient_list,
            )
            email.content_subtype = 'html'
            email.body = html_message
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Renewal invoice sent to {user.email} - Invoice: {invoice_number}")
            return True, f"Invoice {invoice_number} sent successfully"
            
        except Exception as e:
            logger.error(f"Failed to send renewal invoice to {user.email}: {str(e)}")
            return False, f"Failed to send invoice: {str(e)}"
    
    @staticmethod
    def send_bulk_renewal_invoices(user_queryset=None, letterhead_url=None):
        """
        Send renewal invoices to multiple users
        
        Args:
            user_queryset: QuerySet of users (defaults to all active members)
            letterhead_url: Optional URL to letterhead image
            
        Returns:
            dict with success_count, failed_count, and details
        """
        if user_queryset is None:
            # Get all active members (exclude admins and inactive users)
            user_queryset = User.objects.filter(
                is_active=True,
                role='2'  # Members only
            )
        
        success_count = 0
        failed_count = 0
        results = []
        
        for user in user_queryset:
            success, message = MembershipRenewalService.send_renewal_invoice_email(
                user, 
                letterhead_url
            )
            
            if success:
                success_count += 1
            else:
                failed_count += 1
            
            results.append({
                'email': user.email,
                'name': user.full_name,
                'success': success,
                'message': message
            })
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'total': len(results),
            'results': results
        }
    
    @staticmethod
    def get_all_active_members():
        """
        Get all active members for annual renewal reminder
        All members pay subscription annually regardless of join date
        
        Returns:
            QuerySet of users
        """
        members = User.objects.filter(
            is_active=True,
            role='2'  # Members only
        )
        
        return members
