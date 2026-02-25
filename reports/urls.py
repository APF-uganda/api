"""
URL configuration for reports app
Following RESTful conventions with proper endpoint organization
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsAPIView,
    MembershipAnalyticsAPIView,
    ApplicationAnalyticsAPIView,
    SystemAnalyticsAPIView,
    ChartDataAPIView,
    DashboardSummaryAPIView,
    AvailableChartsAPIView,
    AnalyticsHealthCheckAPIView,
    CacheManagementsAPIView,
    ReportTemplateViewSet,
    GeneratedReportViewSet,
    DownloadReportAPIView
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'templates', ReportTemplateViewSet, basename='report-templates')
router.register(r'generated-reports', GeneratedReportViewSet, basename='generated-reports')

# URL patterns
urlpatterns = [
    # Analytics endpoints
    path('analytics/', AnalyticsAPIView.as_view(), name='analytics-comprehensive'),
    path('analytics/membership/', MembershipAnalyticsAPIView.as_view(), name='analytics-membership'),
    path('analytics/applications/', ApplicationAnalyticsAPIView.as_view(), name='analytics-applications'),
    path('analytics/system/', SystemAnalyticsAPIView.as_view(), name='analytics-system'),
    
    # Chart data endpoints
    path('analytics/charts/', ChartDataAPIView.as_view(), name='analytics-charts'),
    path('analytics/charts/available/', AvailableChartsAPIView.as_view(), name='analytics-available-charts'),
    
    # Dashboard endpoints
    path('analytics/summary/', DashboardSummaryAPIView.as_view(), name='dashboard-summary'),
    
    # System endpoints
    path('system/health/', AnalyticsHealthCheckAPIView.as_view(), name='analytics-health'),
    path('system/cache/', CacheManagementsAPIView.as_view(), name='analytics-cache'),
    
    # Report download endpoint
    path('download/<uuid:report_id>/', DownloadReportAPIView.as_view(), name='download-report'),
    
    # Report management endpoints (ViewSets)
    path('', include(router.urls)),
]