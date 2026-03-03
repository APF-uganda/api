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

app_name = 'payments'

urlpatterns = [
    # Payment operations
    path('initiate/', PaymentInitiationView.as_view(), name='payment-initiate'),
    path('status/<uuid:payment_id>/', PaymentStatusView.as_view(), name='payment-status'),
    path('<uuid:payment_id>/retry/', PaymentRetryView.as_view(), name='payment-retry'),
    path('<uuid:payment_id>/cancel/', PaymentCancellationView.as_view(), name='payment-cancel'),
    
    # History
    path('history/', PaymentHistoryView.as_view(), name='payment-history'),
    
    # Webhooks
    path('webhooks/mtn/', MTNWebhookView.as_view(), name='webhook-mtn'),
    path('webhooks/airtel/', AirtelWebhookView.as_view(), name='webhook-airtel'),
    
    # Configuration
    path('membership-fee/', MembershipFeeView.as_view(), name='membership-fee'),
    
    # Admin endpoints
    path('admin/transactions/', AdminTransactionHistoryView.as_view(), name='admin-transactions'),
    path('admin/revenue/', AdminRevenueStatsView.as_view(), name='admin-revenue'),
]
