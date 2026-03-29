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
            #  MEMBERSHIP REPORT
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
                
                queryset = Application.objects.all().prefetch_related('payment_set').order_by('-submitted_at')
                if date_limit:
                    queryset = queryset.filter(submitted_at__gte=date_limit)
                
                results = []
                for app in queryset:
                    
                    payment_obj = app.payment_set.filter(status='completed').first()
                    amt = payment_obj.amount if payment_obj else app.payment_amount or 0
                    
                    results.append({
                        'date': app.submitted_at.strftime('%Y-%m-%d') if app.submitted_at else 'N/A',
                        'reference_id': app.application_id,
                        'name': f"{app.first_name} {app.last_name}",
                        'organization': app.organization or "N/A",
                        'description': f"Application Fee ({app.payment_method or 'Mobile Money'})",
                        'amount_ugx': f"{amt:,.0f}",
                        'status': str(app.payment_status).title(),
                        'raw_amount': float(amt) 
                    })
                return results
            
            #  REVENUE REPORT 
            elif report_type in ['revenue', 'financial', 'payments']:
                from payments.models import Payment, ManualPayment, RenewalProofOfPayment
                
                combined_data = []

                #  Automated Payments
                auto = Payment.objects.filter(status='completed')
                if date_limit: auto = auto.filter(created_at__gte=date_limit)
                
                for p in auto:
                   
                    desc = p.description or p.payment_purpose or f"App Fee ({p.provider.upper()})"
                    if "other services" in desc.lower():
                        desc = "Membership Contribution"

                    combined_data.append({
                        'date': p.created_at.strftime('%Y-%m-%d'),
                        'reference_id': p.application.application_id if p.application else f"TXN-{p.transaction_reference[:10]}",
                        'description': desc,
                        'amount_ugx': f"{p.amount:,.0f}",
                        'payment': "Verified",
                        'raw_amount': float(p.amount) 
                    })

                # Manual Payments 
                manual = ManualPayment.objects.filter(status__in=['verified', 'completed'])
                if date_limit: manual = manual.filter(created_at__gte=date_limit)
                
                for mp in manual:
                    desc = mp.description or mp.get_payment_type_display()
                    combined_data.append({
                        'date': mp.created_at.strftime('%Y-%m-%d'),
                        'reference_id': mp.reference[:15] if mp.reference else "MANUAL-REF",
                        'description': desc, 
                        'amount_ugx': f"{mp.amount:,.0f}",
                        'payment': "Verified",
                        'raw_amount': float(mp.amount)
                    })

                #  Renewals
                renewals = RenewalProofOfPayment.objects.filter(status='approved')
                if date_limit: renewals = renewals.filter(created_at__gte=date_limit)
                
                for r in renewals:
                    combined_data.append({
                        'date': r.created_at.strftime('%Y-%m-%d'),
                        'reference_id': r.invoice_number or "RENEWAL",
                        'description': f"Membership Renewal ({r.get_provider_display()})",
                        'amount_ugx': f"{r.amount:,.0f}",
                        'payment': "Approved",
                        'raw_amount': float(r.amount)
                    })

                combined_data.sort(key=lambda x: x['date'], reverse=True)
                return combined_data

        except Exception as e:
            logger.error(f"Fetcher Error: {str(e)}")
            return [{"Error": f"Database Fetch Error: {str(e)}"}]

        return []