"""
Renewal proof-of-payment views.
Members upload proof → admin approves → invoice marked paid + Payment record created.
"""
import logging
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import RenewalProofOfPayment, Payment
from authentication.permissions import IsAdmin

logger = logging.getLogger(__name__)


# ─── Notification helper ──────────────────────────────────────────────────────

def _send_payment_notification(user, title: str, message: str, notification_type: str = 'success'):
    """Create an in-app UserNotification and send an email to the member."""
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
        logger.warning(f"Failed to create in-app notification for {user.email}: {exc}")

    try:
        from django.core.mail import EmailMultiAlternatives, get_connection
        from django.conf import settings
        from django.utils.html import strip_tags
        user_name = getattr(user, 'full_name', None) or user.email.split('@')[0]
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px">
          <h2 style="color:#5E2590">{title}</h2>
          <p>Dear {user_name},</p>
          <p>{message}</p>
          <p style="color:#888;font-size:12px">APF Uganda Portal</p>
        </div>
        """
        email_msg = EmailMultiAlternatives(
            subject=f"APF Portal — {title}",
            body=strip_tags(html),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@apfportal.com'),
            to=[user.email],
            connection=get_connection(),
        )
        email_msg.attach_alternative(html, "text/html")
        email_msg.send(fail_silently=True)
    except Exception as exc:
        logger.warning(f"Failed to send email notification to {user.email}: {exc}")



# ─── Member endpoints ────────────────────────────────────────────────────────

class MemberInvoiceListView(APIView):
    """GET /api/v1/payments/renewal/invoices/ — member's own invoices"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from admin_management.models import MembershipInvoice
        from admin_management.serializers import MembershipInvoiceSerializer
        invoices = MembershipInvoice.objects.filter(user=request.user).order_by('-invoice_date')
        serializer = MembershipInvoiceSerializer(invoices, many=True)
        return Response(serializer.data)


class UploadRenewalProofView(APIView):
    """POST /api/v1/payments/renewal/upload-proof/ — member uploads proof"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        invoice_number = request.data.get('invoice_number', '').strip()
        provider = request.data.get('provider', 'mtn')
        phone_number = request.data.get('phone_number', '')
        reference_note = request.data.get('reference_note', '')
        proof_file = request.FILES.get('proof_file')

        if not invoice_number:
            return Response({'error': 'invoice_number is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not proof_file:
            return Response({'error': 'proof_file is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate invoice belongs to this user
        from admin_management.models import MembershipInvoice
        try:
            invoice = MembershipInvoice.objects.get(invoice_number=invoice_number, user=request.user)
        except MembershipInvoice.DoesNotExist:
            return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

        if invoice.status == MembershipInvoice.STATUS_PAID:
            return Response({'error': 'This invoice is already paid'}, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing pending proof
        existing = RenewalProofOfPayment.objects.filter(
            user=request.user,
            invoice_number=invoice_number,
            status=RenewalProofOfPayment.STATUS_PENDING
        ).first()
        if existing:
            return Response(
                {'error': 'A proof of payment is already pending review for this invoice'},
                status=status.HTTP_400_BAD_REQUEST
            )

        proof = RenewalProofOfPayment.objects.create(
            user=request.user,
            invoice_number=invoice_number,
            amount=invoice.balance_due,
            provider=provider,
            phone_number=phone_number,
            reference_note=reference_note,
            proof_file=proof_file,
        )

        # Notify all admin users about the new proof of payment
        try:
            from notifications.models import UserNotification
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get all admin users (role='1')
            admin_users = User.objects.filter(role='1', is_active=True)
            
            # Get member name
            member_name = request.user.full_name or request.user.email
            
            # Create notification for each admin with link to manage users page
            for admin in admin_users:
                notification = UserNotification.objects.create(
                    user=admin,
                    title="New Proof of Payment",
                    message=f'{member_name} uploaded proof of payment for invoice {invoice_number}. Click to view in Manage Users.',
                    notification_type="info",
                    priority="medium",
                )
                # Add metadata with action URL
                notification.metadata = {
                    'actionUrl': '/admin/manage-users',
                    'userId': str(request.user.id),
                    'invoiceNumber': invoice_number
                }
                notification.save()
            
            logger.info(f"[RenewalProof] Created admin notifications for {admin_users.count()} admins")
        except Exception as e:
            logger.warning(f"Failed to create admin notifications: {e}")

        return Response({
            'id': proof.id,
            'invoice_number': proof.invoice_number,
            'status': proof.status,
            'message': 'Proof of payment submitted. Pending admin review.',
        }, status=status.HTTP_201_CREATED)


class MemberProofListView(APIView):
    """GET /api/v1/payments/renewal/my-proofs/ — member's submitted proofs"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        proofs = RenewalProofOfPayment.objects.filter(user=request.user)
        data = [_serialize_proof(p) for p in proofs]
        return Response(data)


# ─── Admin endpoints ──────────────────────────────────────────────────────────

class AdminProofListView(APIView):
    """GET /api/v1/payments/renewal/admin/proofs/ — all proofs for admin"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        status_filter = request.query_params.get('status')
        qs = RenewalProofOfPayment.objects.select_related('user', 'reviewed_by').all()
        if status_filter:
            qs = qs.filter(status=status_filter)
        data = [_serialize_proof(p, admin=True) for p in qs]
        return Response(data)


class AdminApproveProofView(APIView):
    """POST /api/v1/payments/renewal/admin/proofs/{id}/approve/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, proof_id):
        proof = get_object_or_404(RenewalProofOfPayment, id=proof_id)

        if proof.status != RenewalProofOfPayment.STATUS_PENDING:
            return Response({'error': 'Proof is not pending review'}, status=status.HTTP_400_BAD_REQUEST)

        from admin_management.models import MembershipInvoice, InvoicePaymentLink
        try:
            invoice = MembershipInvoice.objects.get(invoice_number=proof.invoice_number)
        except MembershipInvoice.DoesNotExist:
            return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

        # Map provider — Payment model only accepts mtn/airtel/pesapal; bank → pesapal as generic
        PROVIDER_MAP = {'mtn': 'mtn', 'airtel': 'airtel', 'bank': 'pesapal'}
        payment_provider = PROVIDER_MAP.get(proof.provider, 'mtn')

        # Create a Payment record using invoice_number as the transaction reference
        payment = Payment.objects.create(
            user=proof.user,
            transaction_reference=f"RENEWAL-{proof.invoice_number}",
            amount=proof.amount,
            currency='UGX',
            provider=payment_provider,
            payment_method=proof.provider,  # store original (mtn/airtel/bank)
            phone_number=proof.phone_number or '0',
            invoice_number=proof.invoice_number,
            status=Payment.STATUS_COMPLETED,
            completed_at=timezone.now(),
        )

        # Link payment to invoice
        InvoicePaymentLink.objects.create(
            invoice=invoice,
            payment=payment,
            amount=proof.amount,
        )

        # Update invoice
        invoice.record_payment(proof.amount)

        # Mark proof approved
        proof.status = RenewalProofOfPayment.STATUS_APPROVED
        proof.reviewed_by = request.user
        proof.review_notes = request.data.get('notes', '')
        proof.reviewed_at = timezone.now()
        proof.save()

        logger.info(f"Renewal proof {proof.id} approved by {request.user.email}. Invoice {invoice.invoice_number} updated.")

        # Notify member
        _send_payment_notification(
            proof.user,
            title="Renewal Payment Approved",
            message=f"Your proof of payment for invoice {proof.invoice_number} (UGX {proof.amount:,.0f}) has been approved. Your membership has been renewed.",
            notification_type="success",
        )

        return Response({
            'message': 'Payment approved. Invoice updated.',
            'invoice_status': invoice.status,
            'payment_reference': payment.transaction_reference,
        })


class AdminRejectProofView(APIView):
    """POST /api/v1/payments/renewal/admin/proofs/{id}/reject/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, proof_id):
        proof = get_object_or_404(RenewalProofOfPayment, id=proof_id)

        if proof.status != RenewalProofOfPayment.STATUS_PENDING:
            return Response({'error': 'Proof is not pending review'}, status=status.HTTP_400_BAD_REQUEST)

        proof.status = RenewalProofOfPayment.STATUS_REJECTED
        proof.reviewed_by = request.user
        proof.review_notes = request.data.get('notes', '')
        proof.reviewed_at = timezone.now()
        proof.save()

        # Notify member
        notes = request.data.get('notes', '')
        reason_text = f" Reason: {notes}" if notes else ""
        _send_payment_notification(
            proof.user,
            title="Renewal Payment Rejected",
            message=f"Your proof of payment for invoice {proof.invoice_number} has been rejected.{reason_text} Please re-upload a valid proof of payment.",
            notification_type="error",
        )

        return Response({'message': 'Proof rejected.'})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _serialize_proof(proof, admin=False):
    data = {
        'id': proof.id,
        'invoice_number': proof.invoice_number,
        'amount': float(proof.amount),
        'provider': proof.provider,
        'phone_number': proof.phone_number,
        'reference_note': proof.reference_note,
        'proof_file_url': proof.proof_file.url if proof.proof_file else None,
        'status': proof.status,
        'review_notes': proof.review_notes,
        'reviewed_at': proof.reviewed_at.isoformat() if proof.reviewed_at else None,
        'created_at': proof.created_at.isoformat(),
    }
    if admin:
        data['member_email'] = proof.user.email
        data['member_name'] = getattr(proof.user, 'full_name', proof.user.email)
        data['reviewed_by'] = proof.reviewed_by.email if proof.reviewed_by else None
    return data
