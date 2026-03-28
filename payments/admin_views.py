"""
Admin views for manual payment management.
"""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import parser_classes
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model

from .models import ManualPayment
from .serializers import ManualPaymentSerializer
from applications.models import Application
from Documents.models import MemberDocument

User = get_user_model()
logger = logging.getLogger(__name__)


class IsAdminRole(BasePermission):
    """Allow access to users with role='1' (admin) or is_staff=True."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (getattr(request.user, 'role', None) == '1' or request.user.is_staff)
        )


def _resolve_payment_user(payment):
    """
    Resolve the user to notify for a payment.
    Priority: payment.user → application.user → User lookup by application email
    """
    if payment.user:
        return payment.user
    if payment.application:
        if payment.application.user:
            return payment.application.user
        # Look up by application email
        if payment.application.email:
            user = User.objects.filter(email=payment.application.email).first()
            if user:
                # Backfill so future lookups are instant
                payment.user = user
                payment.save(update_fields=['user'])
                return user
    return None


def _send_payment_notification(user, title: str, message: str, notification_type: str = 'success',
                               template_name: str = None, template_context: dict = None):
    import logging
    from django.conf import settings
    _log = logging.getLogger(__name__)

    # ── In-app notification ──────────────────────────────────────────────────
    try:
        from notifications.models import UserNotification
        UserNotification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority='high',
        )
    except Exception as exc:
        _log.warning(f"Failed to create in-app notification for {user.email}: {exc}")

    # ── Email ────────────────────────────────────────────────────────────────
    try:
        from django.core.mail import EmailMultiAlternatives, get_connection
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        import datetime

        user_name = getattr(user, 'full_name', None) or user.email.split('@')[0]
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://apf-uganda.onrender.com').rstrip('/')
        dashboard_url = f"{frontend_url}/dashboard"

        if template_name:
            ctx = {
                'user_name': user_name,
                'dashboard_url': dashboard_url,
                'year': datetime.date.today().year,
                **(template_context or {}),
            }
            html = render_to_string(template_name, ctx)
        else:
            # Fallback inline template
            html = f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px">
              <h2 style="color:#5E2590">{title}</h2>
              <p>Dear {user_name},</p>
              <p>{message}</p>
              <p><a href="{dashboard_url}" style="background:#5E2590;color:#fff;padding:10px 20px;
                 border-radius:6px;text-decoration:none;font-weight:bold;">Access Member Dashboard</a></p>
              <p style="color:#888;font-size:12px">APF Uganda Portal</p>
            </div>
            """

        email_msg = EmailMultiAlternatives(
            subject=f"APF Uganda — {title}",
            body=strip_tags(html),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@apfportal.com'),
            to=[user.email],
            connection=get_connection(),
        )
        email_msg.attach_alternative(html, "text/html")
        email_msg.send(fail_silently=True)
    except Exception as exc:
        _log.warning(f"Failed to send email notification to {user.email}: {exc}")


@api_view(['GET'])
@permission_classes([IsAdminRole])
def list_manual_payments(request):
    """
    List all manual payments for admin dashboard.
    """
    try:
        payments = ManualPayment.objects.select_related(
            'application', 'user', 'verified_by'
        ).all()
        
        # Serialize the payments
        payment_data = []
        for payment in payments:
            # Get member name from application or user
            member_name = 'Unknown'
            if payment.application:
                # Use application name if available
                app_name = f"{payment.application.first_name} {payment.application.last_name}".strip()
                if app_name:
                    member_name = app_name
                elif payment.application.user:
                    user_name = f"{payment.application.user.first_name} {payment.application.user.last_name}".strip()
                    member_name = user_name or payment.application.user.email
            elif payment.user:
                # Fallback to payment user
                user_name = f"{payment.user.first_name} {payment.user.last_name}".strip()
                member_name = user_name or payment.user.email

            linked_doc = MemberDocument.objects.filter(
                user=payment.user,
                document_type=f"PAYMENT_RECEIPT_{payment.id}"
            ).order_by('-uploaded_at').first()
            
            payment_data.append({
                'id': payment.id,
                'member_name': member_name,
                'member_email': payment.user.email if payment.user else '',
                'invoice_number': payment.invoice_number,
                'application_id': payment.application_reference or (payment.application.application_id if payment.application else None),
                'reference': payment.reference,
                'description': payment.description,
                'payment_type': payment.payment_type,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'proof_of_payment': payment.proof_of_payment.url if payment.proof_of_payment else None,
                'status': payment.status,
                'created_at': payment.created_at.isoformat(),
                'verified_by': payment.verified_by.email if payment.verified_by else None,
                'verification_notes': payment.verification_notes,
                'requires_document_review': linked_doc is not None,
                'linked_document_id': linked_doc.id if linked_doc else None,
                'linked_document_status': linked_doc.status if linked_doc else None,
            })
        
        return Response(payment_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch payments: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def submit_manual_payment(request):
    """
    Submit a manual renewal payment with proof of payment (member side).
    """
    try:
        proof = request.FILES.get('proof_of_payment')
        if not proof:
            return Response(
                {'error': 'Proof of payment file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        amount = request.data.get('amount')
        if amount is None:
            return Response(
                {'error': 'Amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Resolve user's application for required FK.
        # Priority: explicit application_id -> latest application for user.
        requested_app = str(request.data.get('application_id', '')).strip()
        application = None
        if requested_app:
            application = Application.objects.filter(
                Q(id=requested_app) | Q(application_id=requested_app),
                user=request.user
            ).order_by('-submitted_at').first()
        if not application:
            application = Application.objects.filter(user=request.user).order_by('-submitted_at').first()
        if not application:
            return Response(
                {'error': 'No linked application found for this member account'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice_number = str(request.data.get('invoice_number', '')).strip() or None
        application_reference = application.application_id
        
        # Generate appropriate reference based on payment type
        payment_type = str(request.data.get('payment_type', 'membership_renewal')).strip()
        
        # Validate payment_type
        valid_types = ['membership_renewal', 'donation', 'event', 'other']
        if payment_type not in valid_types:
            payment_type = 'membership_renewal'
        
        # Get or generate reference
        provided_reference = str(request.data.get('reference', '')).strip()
        if provided_reference:
            reference = provided_reference
        elif payment_type == 'donation':
            # Generate unique donation reference
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            reference = f"DON-{timestamp}"
        elif payment_type == 'event':
            # Generate unique event reference
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            reference = f"EVT-{timestamp}"
        elif payment_type == 'other':
            # Generate unique other payment reference
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            reference = f"OTH-{timestamp}"
        elif invoice_number:
            reference = invoice_number
        else:
            reference = application_reference
        
        # Set description based on payment_type (standardized descriptions)
        # Only use user-provided description for 'other' payment type
        user_description = str(request.data.get('description', '')).strip()
        
        if payment_type == 'donation':
            description = 'Donation'
        elif payment_type == 'event':
            # For events, use user description if provided, otherwise generic
            description = user_description or 'Event Payment'
        elif payment_type == 'membership_renewal':
            description = 'Membership Renewal'
        elif payment_type == 'other':
            # For 'other', use user description or generic fallback
            description = user_description or 'Other Payment'
        else:
            description = user_description or 'Payment'

        payment = ManualPayment.objects.create(
            application=application,
            user=request.user,
            amount=amount,
            currency='UGX',
            reference=reference,
            description=description,
            payment_type=payment_type,
            invoice_number=invoice_number,
            application_reference=application_reference,
            proof_of_payment=proof,
            status=ManualPayment.STATUS_PENDING
        )

        # Also register this receipt in member documents so it appears
        # under "documents pending review" in the admin document workflow.
        if hasattr(proof, 'seek'):
            proof.seek(0)
        original_name = getattr(proof, 'name', '') or 'receipt'
        member_document = MemberDocument.objects.create(
            user=request.user,
            file=proof,
            file_name=f"Renewal Receipt - {reference} - {original_name}",
            file_size=getattr(proof, 'size', 0) or 0,
            file_type=getattr(proof, 'content_type', '') or '',
            document_type=f"PAYMENT_RECEIPT_{payment.id}",
            status='pending',
            admin_feedback=''
        )

        # Notify admins about the new proof of payment
        try:
            from notifications.admin_notification_service import notify_admin_payment_proof
            notify_admin_payment_proof(
                user=request.user,
                payment_type=payment_type,
                amount=float(amount),
                reference=reference
            )
            logger.info(f"[ManualPayment] Notified admins about payment proof from {request.user.email}")
        except Exception as e:
            logger.warning(f"[ManualPayment] Failed to notify admins: {e}")

        payload = {
            'id': payment.id,
            'reference': payment.reference,
            'description': payment.description,
            'amount': float(payment.amount),
            'currency': payment.currency,
            'status': payment.status,
            'invoice_number': payment.invoice_number,
            'application_reference': payment.application_reference,
            'proof_of_payment': payment.proof_of_payment.url if payment.proof_of_payment else None,
            'member_document_id': member_document.id,
            'created_at': payment.created_at.isoformat(),
        }
        return Response(payload, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {'error': f'Failed to submit manual payment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_member_manual_payments(request):
    """
    List current member's manual payments (renewals + application-linked records).
    """
    try:
        payments = ManualPayment.objects.select_related('application').filter(user=request.user).order_by('-created_at')
        payment_data = [
            {
                'id': payment.id,
                'reference': payment.reference,
                'description': payment.description,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'status': payment.status,
                'invoice_number': payment.invoice_number,
                'application_reference': payment.application_reference or (payment.application.application_id if payment.application else None),
                'proof_of_payment': payment.proof_of_payment.url if payment.proof_of_payment else None,
                'created_at': payment.created_at.isoformat(),
                'verified_at': payment.verified_at.isoformat() if payment.verified_at else None,
            }
            for payment in payments
        ]
        return Response({'results': payment_data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch member payments: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminRole])
def verify_payment(request, payment_id):
    """
    Verify a manual payment.
    """
    try:
        payment = ManualPayment.objects.get(id=payment_id)

        linked_doc = MemberDocument.objects.filter(
            user=payment.user,
            document_type=f"PAYMENT_RECEIPT_{payment.id}"
        ).order_by('-uploaded_at').first()
        if linked_doc is not None:
            return Response(
                {'error': 'This payment is verified via Document Review. Approve the linked receipt document instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if payment.status != ManualPayment.STATUS_PENDING:
            return Response(
                {'error': 'Payment is not in pending status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notes = request.data.get('notes', '')
        payment.verify(request.user, notes)
        
        # Notify member
        user = _resolve_payment_user(payment)
        if user:
            _send_payment_notification(
                user,
                title="Application Payment Approved",
                message=f"Your application payment of {payment.currency} {payment.amount:,.0f} has been verified and approved. Welcome to APF Uganda!",
                notification_type="success",
                template_name="emails/payment_approved.html",
                template_context={
                    'amount': f"{payment.amount:,.0f}",
                    'reference': payment.application_reference or payment.reference or '',
                },
            )
        
        return Response(
            {'message': 'Payment verified successfully'},
            status=status.HTTP_200_OK
        )
        
    except ManualPayment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to verify payment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminRole])
def reject_payment(request, payment_id):
    """
    Reject a manual payment.
    """
    try:
        payment = ManualPayment.objects.get(id=payment_id)

        linked_doc = MemberDocument.objects.filter(
            user=payment.user,
            document_type=f"PAYMENT_RECEIPT_{payment.id}"
        ).order_by('-uploaded_at').first()
        if linked_doc is not None:
            return Response(
                {'error': 'This payment is reviewed via Document Review. Reject the linked receipt document instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if payment.status != ManualPayment.STATUS_PENDING:
            return Response(
                {'error': 'Payment is not in pending status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notes = request.data.get('notes', '')
        payment.reject(request.user, notes)
        
        # Notify member
        user = _resolve_payment_user(payment)
        if user:
            reason_text = f" Reason: {notes}" if notes else ""
            _send_payment_notification(
                user,
                title="Application Payment Rejected",
                message=f"Your application payment has been rejected.{reason_text} Please contact support or re-submit your payment.",
                notification_type="error",
                template_name="emails/payment_rejected.html",
                template_context={
                    'amount': f"{payment.amount:,.0f}",
                    'reference': payment.application_reference or payment.reference or '',
                    'reason': notes or '',
                },
            )
        
        return Response(
            {'message': 'Payment rejected successfully'},
            status=status.HTTP_200_OK
        )
        
    except ManualPayment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to reject payment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminRole])
def get_revenue_stats(request):
    """
    Get total revenue from all completed/verified payments.
    """
    try:
        from payments.models import Payment
        payment_revenue = float(
            Payment.objects.filter(
                status=Payment.STATUS_COMPLETED
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        manual_revenue = float(
            ManualPayment.objects.filter(
                status=ManualPayment.STATUS_VERIFIED
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        return Response(
            {'total_revenue': payment_revenue + manual_revenue},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch revenue: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminRole])
def get_payment_statistics(request):
    """
    Get comprehensive payment statistics with growth rates and trends.
    Counts ALL money received:
      - Payment (completed) — mobile money + approved renewal proofs
      - ManualPayment (verified) — bank/manual uploads
    Percentage change = this month vs previous month (30-day windows).
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        from payments.models import Payment

        now = timezone.now()
        last_month = now - timedelta(days=30)
        prev_month_start = now - timedelta(days=60)

        # ── Totals ────────────────────────────────────────────────────────────
        total_manual = ManualPayment.objects.count()
        total_payments = Payment.objects.count()
        total_transactions = total_manual + total_payments

        pending_payments = ManualPayment.objects.filter(status=ManualPayment.STATUS_PENDING).count()
        verified_payments = ManualPayment.objects.filter(status=ManualPayment.STATUS_VERIFIED).count()

        payment_revenue = Payment.objects.filter(
            status=Payment.STATUS_COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or 0

        manual_revenue = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_VERIFIED
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_revenue = float(payment_revenue) + float(manual_revenue)

        pending_revenue = float(
            ManualPayment.objects.filter(
                status=ManualPayment.STATUS_PENDING
            ).aggregate(total=Sum('amount'))['total'] or 0
        )

        # ── This month (last 30 days) ─────────────────────────────────────────
        this_payment = float(
            Payment.objects.filter(
                status=Payment.STATUS_COMPLETED,
                completed_at__gte=last_month,
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        this_manual = float(
            ManualPayment.objects.filter(
                status=ManualPayment.STATUS_VERIFIED,
                verified_at__gte=last_month,
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        this_month_revenue = this_payment + this_manual

        # ── Previous month (30–60 days ago) ──────────────────────────────────
        prev_payment = float(
            Payment.objects.filter(
                status=Payment.STATUS_COMPLETED,
                completed_at__gte=prev_month_start,
                completed_at__lt=last_month,
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        prev_manual = float(
            ManualPayment.objects.filter(
                status=ManualPayment.STATUS_VERIFIED,
                verified_at__gte=prev_month_start,
                verified_at__lt=last_month,
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        prev_month_revenue = prev_payment + prev_manual

        # ── Transaction counts for growth ─────────────────────────────────────
        last_month_new = (
            ManualPayment.objects.filter(created_at__gte=last_month).count() +
            Payment.objects.filter(created_at__gte=last_month).count()
        )
        prev_month_new = (
            ManualPayment.objects.filter(
                created_at__gte=prev_month_start, created_at__lt=last_month
            ).count() +
            Payment.objects.filter(
                created_at__gte=prev_month_start, created_at__lt=last_month
            ).count()
        )

        previous_pending = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_PENDING,
            created_at__lt=last_month
        ).count()

        def calculate_growth_rate(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)

        revenue_growth = calculate_growth_rate(this_month_revenue, prev_month_revenue)
        transactions_growth = calculate_growth_rate(last_month_new, prev_month_new)
        pending_growth = calculate_growth_rate(pending_payments, previous_pending)

        return Response({
            'total_transactions': total_transactions,
            'pending_revenue': pending_revenue,
            'total_revenue': total_revenue,
            'verified_payments': verified_payments,
            'pending_payments': pending_payments,
            'growth_rates': {
                'transactions': transactions_growth,
                'pending': pending_growth,
                'revenue': revenue_growth,
            },
            'last_month_stats': {
                'new_transactions': last_month_new,
                'new_revenue': this_month_revenue,
                'verified_payments': verified_payments,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'Failed to fetch payment statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
