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
def get_payment_statistics(request):
    """
    Get comprehensive payment statistics with growth rates and trends.
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        last_month = now - timedelta(days=30)
        
        # Current statistics
        total_payments = ManualPayment.objects.count()
        pending_payments = ManualPayment.objects.filter(status=ManualPayment.STATUS_PENDING).count()
        verified_payments = ManualPayment.objects.filter(status=ManualPayment.STATUS_VERIFIED).count()
        
        # Current revenue
        total_revenue = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_VERIFIED
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        pending_revenue = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_PENDING
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Last month statistics for comparison
        last_month_total = ManualPayment.objects.filter(
            created_at__gte=last_month
        ).count()
        
        last_month_verified = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_VERIFIED,
            updated_at__gte=last_month
        ).count()
        
        last_month_revenue = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_VERIFIED,
            updated_at__gte=last_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate growth rates
        def calculate_growth_rate(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)
        
        # For transactions, compare current total vs previous month's additions
        transactions_growth = calculate_growth_rate(total_payments, total_payments - last_month_total)
        
        # For revenue, compare current total vs (current total - last month additions)
        previous_revenue = total_revenue - last_month_revenue
        revenue_growth = calculate_growth_rate(float(total_revenue), float(previous_revenue))
        
        # For pending, we'll use a simple month-over-month comparison
        # Get pending count from 30 days ago (approximate)
        previous_pending = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_PENDING,
            created_at__lt=last_month
        ).count()
        pending_growth = calculate_growth_rate(pending_payments, previous_pending)
        
        # Debug logging
        print(f"Payment Statistics Debug:")
        print(f"  Total Revenue: {total_revenue}, Previous: {previous_revenue}, Growth: {revenue_growth}%")
        print(f"  Total Transactions: {total_payments}, Last Month New: {last_month_total}, Growth: {transactions_growth}%")
        print(f"  Pending: {pending_payments}, Previous: {previous_pending}, Growth: {pending_growth}%")
        
        return Response({
            'total_transactions': total_payments,
            'pending_revenue': float(pending_revenue),
            'total_revenue': float(total_revenue),
            'verified_payments': verified_payments,
            'pending_payments': pending_payments,
            'growth_rates': {
                'transactions': transactions_growth,
                'pending': pending_growth,
                'revenue': revenue_growth,
            },
            'last_month_stats': {
                'new_transactions': last_month_total,
                'new_revenue': float(last_month_revenue),
                'verified_payments': last_month_verified,
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch payment statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )