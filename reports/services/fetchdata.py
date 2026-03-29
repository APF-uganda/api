from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class ReportDataFetcher:
    @staticmethod
    def get_data(template, filters_applied=None):
        report_type = str(template.report_type).lower()
        filters = filters_applied or {}
        
        def get_date_limit(period_label):
            now = timezone.now()
            p = str(period_label or '').lower()
            if '7' in p: return now - timedelta(days=7)
            if '30' in p: return now - timedelta(days=30)
            if '90' in p: return now - timedelta(days=90)
            if '12' in p: return now - timedelta(days=365)
            return None

        date_limit = get_date_limit(filters.get('period'))

        try:
            # MEMBERSHIP REPORT
            if report_type == 'membership':
                queryset = User.objects.all().order_by('created_at')
                if date_limit:
                    queryset = queryset.filter(created_at__gte=date_limit)
                
                data = list(queryset.values('email', 'first_name', 'last_name', 'created_at'))
                for item in data:
                    if item.get('created_at'):
                        item['joined_date'] = item['created_at'].strftime('%Y-%m-%d')
                return data
            
            # APPLICATIONS REPORT
            elif report_type == 'applications':
                from applications.models import Application
                
                queryset = Application.objects.all().order_by('-submitted_at')
                if date_limit:
                    queryset = queryset.filter(submitted_at__gte=date_limit)
                
               
                data = list(queryset.values(
                    'application_id', 'first_name', 'last_name', 
                    'organization', 'payment_status', 'submitted_at',
                    'payment_amount', 'payment_method'
                ))
                
                for item in data:
                    amt = item.get('payment_amount', 0)
                    item['amount_ugx'] = f"{amt:,.0f}" # Fixed formatting
                    item['description'] = f"Application Fee ({item.get('payment_method', 'N/A')})"
                    item['payment'] = str(item.get('payment_status', 'Pending')).title()
                    
                    if item.get('submitted_at'):
                        item['date'] = item['submitted_at'].strftime('%Y-%m-%d')
                return data
            
            #  REVENUE REPORT
            elif report_type in ['revenue', 'financial', 'payments']:
                from payments.models import Payment, ManualPayment, RenewalProofOfPayment
                
                combined_data = []

               
                auto = Payment.objects.filter(status='completed')
                if date_limit: auto = auto.filter(created_at__gte=date_limit)
                
                for p in auto:
                    reason = "Application Fee"
                    if p.invoice_number: reason = f"Invoice {p.invoice_number}"
                    
                    combined_data.append({
                        'date': p.created_at.strftime('%Y-%m-%d'),
                        'application_id': p.transaction_reference[:15],
                        'description': f"{reason} ({p.provider.upper()})",
                        'amount_ugx': f"{p.amount:,.0f}",
                        'payment': "Success",
                        'raw_amount': float(p.amount) 
                    })

             
                manual = ManualPayment.objects.filter(status='verified')
                if date_limit: manual = manual.filter(created_at__gte=date_limit)
                
                for mp in manual:
                    combined_data.append({
                        'date': mp.created_at.strftime('%Y-%m-%d'),
                        'application_id': mp.reference[:15],
                        'description': mp.get_payment_type_display(), 
                        'amount_ugx': f"{mp.amount:,.0f}",
                        'payment': "Verified",
                        'raw_amount': float(mp.amount)
                    })

               
                renewals = RenewalProofOfPayment.objects.filter(status='approved')
                if date_limit: renewals = renewals.filter(created_at__gte=date_limit)
                
                for r in renewals:
                    combined_data.append({
                        'date': r.created_at.strftime('%Y-%m-%d'),
                        'application_id': r.invoice_number,
                        'description': f"Renewal ({r.get_provider_display()})",
                        'amount_ugx': f"{r.amount:,.0f}",
                        'payment': "Approved",
                        'raw_amount': float(r.amount)
                    })

               
                combined_data.sort(key=lambda x: x['date'], reverse=True)
                return combined_data

        except Exception as e:
            logger.error(f"Fetcher Error: {str(e)}")
            return [{"Error": f"Database Fetch Error: {str(e)}"}]

        return [{"Message": f"No data found for category: {report_type}"}]