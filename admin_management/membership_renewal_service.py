"""
Membership Renewal Service
Handles sending membership renewal invoices via email and creating invoice records
"""
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
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
    def generate_invoice_number(user_id=None):
        """
        Generate unique invoice number
        Format: INV-YYYY-MMDDHHMMSS or INV-YYYY-USERID-MMDDHHMMSS
        """
        current_year = datetime.now().year
        timestamp = datetime.now().strftime('%m%d%H%M%S')
        
        if user_id:
            return f"INV-{current_year}-{user_id}-{timestamp}"
        return f"INV-{current_year}-{timestamp}"
    
    @staticmethod
    def create_membership_invoice(user, send_email=True):
        """
        Create a membership renewal invoice record in the database
        
        Args:
            user: User object
            send_email: Whether to send email notification
            
        Returns:
            tuple (invoice_object, success: bool, message: str)
        """
        from admin_management.models import MembershipInvoice
        
        try:
            # Get next membership year
            next_start_year, next_end_year = MembershipRenewalService.get_next_membership_year()
            
            # Check if invoice already exists for this period
            period_start = date(next_start_year, 4, 1)
            period_end = date(next_end_year, 3, 31)
            
            existing_invoice = MembershipInvoice.objects.filter(
                user=user,
                period_start=period_start,
                period_end=period_end
            ).first()
            
            if existing_invoice:
                logger.info(f"Invoice already exists for {user.email}: {existing_invoice.invoice_number}")
                return existing_invoice, True, f"Invoice {existing_invoice.invoice_number} already exists"
            
            # Calculate amounts
            amounts = MembershipRenewalService.calculate_renewal_amount(user)
            
            # Generate invoice number
            invoice_number = MembershipRenewalService.generate_invoice_number(user.id)
            
            # Create invoice record
            invoice = MembershipInvoice.objects.create(
                invoice_number=invoice_number,
                user=user,
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=30),
                period_start=period_start,
                period_end=period_end,
                base_amount=Decimal(str(amounts['base_amount'])),
                previous_balance=Decimal(str(amounts['previous_balance'])),
                discount=Decimal(str(amounts['discount'])),
                total_amount=Decimal(str(amounts['total'])),
                amount_paid=Decimal('0.00'),
                balance_due=Decimal(str(amounts['total'])),
                status=MembershipInvoice.STATUS_PENDING
            )
            
            logger.info(f"Created invoice {invoice_number} for {user.email}")
            
            # Send email if requested
            if send_email:
                email_success, email_message = MembershipRenewalService.send_renewal_invoice_email(
                    user, 
                    invoice=invoice
                )
                
                if email_success:
                    invoice.email_sent = True
                    invoice.email_sent_at = timezone.now()
                    invoice.save()
                
                return invoice, email_success, email_message
            
            return invoice, True, f"Invoice {invoice_number} created successfully"
            
        except Exception as e:
            logger.error(f"Failed to create invoice for {user.email}: {str(e)}")
            return None, False, f"Failed to create invoice: {str(e)}"
    
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
    def send_renewal_invoice_email(user, letterhead_url=None, invoice=None):
        """
        Send membership renewal invoice email to a user
        
        Args:
            user: User object
            letterhead_url: Optional URL to letterhead image
            invoice: Optional MembershipInvoice object (if not provided, creates one)
            
        Returns:
            tuple (success: bool, message: str)
        """
        try:
            # Create invoice if not provided
            if invoice is None:
                invoice, created, message = MembershipRenewalService.create_membership_invoice(
                    user, 
                    send_email=False
                )
                if not created:
                    return False, message
            
            # Get membership years from invoice
            renewal_period = f"Apr {invoice.period_start.year} - Mar {invoice.period_end.year}"
            
            # Prepare email context
            context = {
                'user': user,
                'invoice_number': invoice.invoice_number,
                'invoice_date': invoice.invoice_date.strftime('%d/%m/%Y'),
                'due_date': invoice.due_date.strftime('%d/%m/%Y'),
                'renewal_period': renewal_period,
                'membership_type': getattr(user, 'membership_category', 'Full Member'),
                'membership_number': getattr(user, 'icpau_registration_number', ''),
                'base_amount': invoice.base_amount,
                'previous_balance': invoice.previous_balance,
                'discount': invoice.discount,
                'total_amount': invoice.total_amount,
                'letterhead_url': letterhead_url,
                'frontend_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3001'),
            }
            
            # Render email template
            html_message = render_to_string('emails/membership_renewal_invoice.html', context)
            text_message = render_to_string('emails/membership_renewal_invoice.txt', context)
            
            # Create email with proper multipart structure
            subject = f'Membership Renewal Invoice - {renewal_period}'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            
            # Create multipart email (text + HTML)
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,  # Plain text version
                from_email=from_email,
                to=recipient_list,
            )
            # Attach HTML version as alternative
            email.attach_alternative(html_message, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Renewal invoice sent to {user.email} - Invoice: {invoice.invoice_number}")
            return True, f"Invoice {invoice.invoice_number} sent successfully"
            
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
