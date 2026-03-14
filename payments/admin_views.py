"""
Admin views for manual payment management.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model

from .models import ManualPayment
from .serializers import ManualPaymentSerializer

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
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
            
            payment_data.append({
                'id': payment.id,
                'member_name': member_name,
                'member_email': payment.user.email if payment.user else '',
                'invoice_number': getattr(payment, 'invoice_number', None),
                'application_id': getattr(payment, 'application_reference', None) or (payment.application.application_id if payment.application else None),
                'reference': payment.reference,
                'description': getattr(payment, 'description', 'Application Fee'),
                'amount': float(payment.amount),
                'currency': payment.currency,
                'proof_of_payment': payment.proof_of_payment.url if payment.proof_of_payment else None,
                'status': payment.status,
                'created_at': payment.created_at.isoformat(),
                'verified_by': payment.verified_by.username if payment.verified_by else None,
                'verification_notes': payment.verification_notes,
            })
        
        return Response(payment_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch payments: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def verify_payment(request, payment_id):
    """
    Verify a manual payment.
    """
    try:
        payment = ManualPayment.objects.get(id=payment_id)
        
        if payment.status != ManualPayment.STATUS_PENDING:
            return Response(
                {'error': 'Payment is not in pending status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notes = request.data.get('notes', '')
        payment.verify(request.user, notes)
        
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
@permission_classes([IsAuthenticated, IsAdminUser])
def reject_payment(request, payment_id):
    """
    Reject a manual payment.
    """
    try:
        payment = ManualPayment.objects.get(id=payment_id)
        
        if payment.status != ManualPayment.STATUS_PENDING:
            return Response(
                {'error': 'Payment is not in pending status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notes = request.data.get('notes', '')
        payment.reject(request.user, notes)
        
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
@permission_classes([IsAuthenticated, IsAdminUser])
def get_revenue_stats(request):
    """
    Get total revenue from verified manual payments.
    """
    try:
        total_revenue = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_VERIFIED
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return Response(
            {'total_revenue': float(total_revenue)},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch revenue: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_pending_count(request):
    """
    Get count of pending manual payments.
    """
    try:
        pending_count = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_PENDING
        ).count()
        
        return Response(
            {'pending': pending_count},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch pending count: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )