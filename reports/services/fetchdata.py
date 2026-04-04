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
                    else:
                        item['joined_date'] = 'N/A'
                return data
            
            # APPLICATIONS REPORT 
            elif report_type == 'applications':
                from applications.models import Application
                queryset = Application.objects.all().select_related('current_payment').order_by('-submitted_at')
                if date_limit:
                    queryset = queryset.filter(submitted_at__gte=date_limit)
                
                results = []
                for app in queryset:
                    amt = app.payment_amount if app.payment_amount is not None else 0
                    results.append({
                        'date': app.submitted_at.strftime('%Y-%m-%d') if app.submitted_at else 'N/A',
                        'reference_id': app.application_id,
                        'name': f"{app.first_name} {app.last_name}",
                        'organization': app.organization or "N/A",
                        'description': f"App Fee ({app.payment_method or 'Manual'})",
                        'amount_ugx': f"{float(amt):,.0f}",
                        'status': str(app.status or 'Pending').title(),
                        'payment': str(app.payment_status or 'Idle').title(),
                        'raw_amount': float(amt) 
                    })
                return results
            
            # REVENUE / FINANCIAL REPORTS 
            elif report_type in ['revenue', 'financial', 'payments']:
                from payments.models import Payment, ManualPayment, RenewalProofOfPayment
                combined_data = []

                # Automated Payments (Mobile Money/Cards)
                auto = Payment.objects.filter(status='completed')
                if date_limit: 
                    auto = auto.filter(created_at__gte=date_limit)
                
                for p in auto:
                  
                    combined_data.append({
                        'date': p.created_at.strftime('%Y-%m-%d') if p.created_at else 'N/A',
                        'reference_id': p.transaction_reference if p.transaction_reference else "TXN-REF",
                        'description': p.payment_method.upper() if p.payment_method else "Mobile Money",
                        'amount_ugx': f"{float(p.amount or 0):,.0f}",
                        'payment': "Verified",
                        'raw_amount': float(p.amount or 0) 
                    })

                # Manual Payments 
                manual = ManualPayment.objects.filter(status='verified')
                if date_limit: 
                    manual = manual.filter(created_at__gte=date_limit)
                
                for mp in manual:

                    actual_desc = mp.description if mp.description and mp.description not in ["1", ""] else mp.get_payment_type_display()
                    
                    combined_data.append({
                        'date': mp.created_at.strftime('%Y-%m-%d') if mp.created_at else 'N/A',
                        'reference_id': mp.reference if mp.reference else "MANUAL",
                        'description': actual_desc, 
                        'amount_ugx': f"{float(mp.amount or 0):,.0f}",
                        'payment': "Verified",
                        'raw_amount': float(mp.amount or 0)
                    })

                # Renewals
                renewals = RenewalProofOfPayment.objects.filter(status='approved')
                if date_limit: 
                    renewals = renewals.filter(created_at__gte=date_limit)
                
                for r in renewals:
                    combined_data.append({
                        'date': r.created_at.strftime('%Y-%m-%d') if r.created_at else 'N/A',
                        'reference_id': r.invoice_number or "RENEWAL",
                        'description': "Membership Renewal",
                        'amount_ugx': f"{float(r.amount or 0):,.0f}",
                        'payment': "Approved",
                        'raw_amount': float(r.amount or 0)
                    })

                combined_data.sort(key=lambda x: x['date'] if x['date'] != 'N/A' else '1900-01-01', reverse=True)
                return combined_data

        except Exception as e:
            logger.error(f"Fetcher Error: {str(e)}")
            return [{"Error": f"Database Fetch Error: {str(e)}"}]

        return []