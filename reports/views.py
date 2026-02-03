"""
Reports and Analytics Views
Following SOLID principles with proper separation of concerns
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from authentication.permissions import IsAuthenticated, IsAdmin
from .services.analytics_coordinator import analytics_coordinator
from .models import ReportTemplate, GeneratedReport
from .serializers import ReportTemplateSerializer, GeneratedReportSerializer


class AnalyticsAPIView(APIView):
    """
    Main analytics API endpoint
    Single Responsibility: Handles analytics data requests
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Get comprehensive analytics data",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period (7d, 30d, 90d, 12m)",
                type=openapi.TYPE_STRING,
                default='30d'
            )
        ]
    )
    def get(self, request):
        """Get comprehensive analytics data"""
        period = request.query_params.get('period', '30d')
        
        try:
            analytics_data = analytics_coordinator.get_comprehensive_analytics(period)
            return Response(analytics_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch analytics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MembershipAnalyticsAPIView(APIView):
    """
    Membership-specific analytics endpoint
    Single Responsibility: Handles membership analytics
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Get membership analytics data",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period (7d, 30d, 90d, 12m)",
                type=openapi.TYPE_STRING,
                default='30d'
            )
        ]
    )
    def get(self, request):
        """Get membership analytics data"""
        period = request.query_params.get('period', '30d')
        
        try:
            analytics_data = analytics_coordinator.get_service_metrics('membership', period)
            return Response(analytics_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch membership analytics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ApplicationAnalyticsAPIView(APIView):
    """
    Application-specific analytics endpoint
    Single Responsibility: Handles application analytics
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Get application analytics data",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period (7d, 30d, 90d, 12m)",
                type=openapi.TYPE_STRING,
                default='30d'
            )
        ]
    )
    def get(self, request):
        """Get application analytics data"""
        period = request.query_params.get('period', '30d')
        
        try:
            analytics_data = analytics_coordinator.get_service_metrics('applications', period)
            return Response(analytics_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch application analytics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SystemAnalyticsAPIView(APIView):
    """
    System-specific analytics endpoint
    Single Responsibility: Handles system analytics
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Get system analytics data",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period (7d, 30d, 90d, 12m)",
                type=openapi.TYPE_STRING,
                default='30d'
            )
        ]
    )
    def get(self, request):
        """Get system analytics data"""
        period = request.query_params.get('period', '30d')
        
        try:
            analytics_data = analytics_coordinator.get_service_metrics('system', period)
            return Response(analytics_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch system analytics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChartDataAPIView(APIView):
    """
    Chart data endpoint
    Single Responsibility: Provides chart data for visualizations
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Get chart data for visualizations",
        manual_parameters=[
            openapi.Parameter(
                'type',
                openapi.IN_QUERY,
                description="Chart type",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period (7d, 30d, 90d, 12m)",
                type=openapi.TYPE_STRING,
                default='30d'
            ),
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="Analytics category (membership, applications, system)",
                type=openapi.TYPE_STRING
            )
        ]
    )
    def get(self, request):
        """Get chart data for visualizations"""
        chart_type = request.query_params.get('type')
        period = request.query_params.get('period', '30d')
        category = request.query_params.get('category')
        
        if not chart_type:
            return Response(
                {'error': 'Chart type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            chart_data = analytics_coordinator.get_chart_data(chart_type, period, category)
            return Response(chart_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch chart data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardSummaryAPIView(APIView):
    """
    Dashboard summary endpoint
    Single Responsibility: Provides dashboard summary data
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Get dashboard summary data"
    )
    def get(self, request):
        """Get dashboard summary data"""
        try:
            summary_data = analytics_coordinator.get_dashboard_summary()
            return Response(summary_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch dashboard summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AvailableChartsAPIView(APIView):
    """
    Available charts endpoint
    Single Responsibility: Lists available chart types
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Get list of available chart types"
    )
    def get(self, request):
        """Get list of available chart types"""
        try:
            charts = analytics_coordinator.get_available_charts()
            return Response(charts)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch available charts: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyticsHealthCheckAPIView(APIView):
    """
    Analytics health check endpoint
    Single Responsibility: Provides health status of analytics services
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Check health of analytics services"
    )
    def get(self, request):
        """Check health of analytics services"""
        try:
            health_data = analytics_coordinator.health_check()
            return Response(health_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to check analytics health: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CacheManagementsAPIView(APIView):
    """
    Cache management endpoint
    Single Responsibility: Manages analytics cache
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Get cache statistics"
    )
    def get(self, request):
        """Get cache statistics"""
        try:
            cache_stats = analytics_coordinator.get_cache_stats()
            return Response(cache_stats)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch cache stats: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        tags=["Analytics"],
        operation_description="Clear analytics cache"
    )
    def delete(self, request):
        """Clear analytics cache"""
        try:
            analytics_coordinator.clear_cache()
            return Response({'message': 'Cache cleared successfully'})
        except Exception as e:
            return Response(
                {'error': f'Failed to clear cache: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for report templates
    Single Responsibility: Manages report templates
    """
    serializer_class = ReportTemplateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        """Get report templates based on user permissions"""
        user = self.request.user
        if user.role == '1':  # Admin
            return ReportTemplate.objects.filter(is_active=True)
        else:
            return ReportTemplate.objects.filter(
                is_active=True,
                created_by=user
            )
    
    def perform_create(self, serializer):
        """Set created_by when creating template"""
        serializer.save(created_by=self.request.user)


class GeneratedReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for generated reports (read-only)
    Single Responsibility: Manages generated reports viewing
    """
    serializer_class = GeneratedReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        """Get generated reports based on user permissions"""
        user = self.request.user
        if user.role == '1':  # Admin
            return GeneratedReport.objects.all()
        else:
            return GeneratedReport.objects.filter(generated_by=user)
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Track download of a report"""
        report = self.get_object()
        
        # Update download count and timestamp
        report.download_count += 1
        report.last_downloaded_at = timezone.now()
        report.save(update_fields=['download_count', 'last_downloaded_at'])
        
        return Response({
            'message': 'Download tracked',
            'download_count': report.download_count,
            'file_path': report.file_path
        })