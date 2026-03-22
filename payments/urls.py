"""
URL configuration for payments app.
"""
from django.urls import path
from .views import (
    PaymentInitiationView,
    PaymentStatusView,
    PaymentRetryView,
    PaymentCancellationView,
    MTNWebhookView,
    AirtelWebhookView,
    MembershipFeeView,
    PaymentHistoryView,
    AdminTransactionHistoryView,
    AdminRevenueStatsView
)
from .views_webhook import (
    EnhancedMTNWebhookView,
    EnhancedAirtelWebhookView,
    PesaPalWebhookView
)
from .admin_views import (
    list_manual_payments,
    submit_manual_payment,
    list_member_manual_payments,
    verify_payment,
    reject_payment,
    get_revenue_stats,
    get_payment_statistics
)
from .renewal_views import (
    MemberInvoiceListView,
    UploadRenewalProofView,
    MemberProofListView,
    AdminProofListView,
    AdminApproveProofView,
    AdminRejectProofView,
)

app_name = 'payments'

urlpatterns = [
    # Member manual payment endpoints (receipt upload flow)
    path('manual/submit/', submit_manual_payment, name='member-manual-payment-submit'),
    path('manual/history/', list_member_manual_payments, name='member-manual-payment-history'),

    # Manual payment admin endpoints (NEW - for admin dashboard)
    path('', list_manual_payments, name='manual-payments-list'),
    path('<int:payment_id>/verify/', verify_payment, name='manual-payment-verify'),
    path('<int:payment_id>/reject/', reject_payment, name='manual-payment-reject'),
    path('revenue/', get_revenue_stats, name='manual-payment-revenue'),
    path('statistics/', get_payment_statistics, name='payment-statistics'),

    # Renewal proof-of-payment (member)
    path('renewal/invoices/', MemberInvoiceListView.as_view(), name='renewal-invoices'),
    path('renewal/upload-proof/', UploadRenewalProofView.as_view(), name='renewal-upload-proof'),
    path('renewal/my-proofs/', MemberProofListView.as_view(), name='renewal-my-proofs'),

    # Renewal proof-of-payment (admin)
    path('renewal/admin/proofs/', AdminProofListView.as_view(), name='renewal-admin-proofs'),
    path('renewal/admin/proofs/<int:proof_id>/approve/', AdminApproveProofView.as_view(), name='renewal-admin-approve'),
    path('renewal/admin/proofs/<int:proof_id>/reject/', AdminRejectProofView.as_view(), name='renewal-admin-reject'),

    # Mobile money payment operations (EXISTING)
    path('mobile/initiate/', PaymentInitiationView.as_view(), name='payment-initiate'),
    path('mobile/status/<uuid:payment_id>/', PaymentStatusView.as_view(), name='payment-status'),
    path('mobile/<uuid:payment_id>/retry/', PaymentRetryView.as_view(), name='payment-retry'),
    path('mobile/<uuid:payment_id>/cancel/', PaymentCancellationView.as_view(), name='payment-cancel'),

    # History
    path('mobile/history/', PaymentHistoryView.as_view(), name='payment-history'),

    # Webhooks
    path('webhooks/mtn/', MTNWebhookView.as_view(), name='webhook-mtn'),
    path('webhooks/airtel/', AirtelWebhookView.as_view(), name='webhook-airtel'),
    path('webhooks/pesapal/', PesaPalWebhookView.as_view(), name='webhook-pesapal'),

    # Enhanced webhooks (v2)
    path('webhooks/v2/mtn/', EnhancedMTNWebhookView.as_view(), name='webhook-mtn-v2'),
    path('webhooks/v2/airtel/', EnhancedAirtelWebhookView.as_view(), name='webhook-airtel-v2'),

    # Configuration
    path('membership-fee/', MembershipFeeView.as_view(), name='membership-fee'),

    # Legacy admin endpoints (for mobile money transactions)
    path('admin/transactions/', AdminTransactionHistoryView.as_view(), name='admin-transactions'),
    path('admin/revenue/', AdminRevenueStatsView.as_view(), name='admin-revenue'),
]
