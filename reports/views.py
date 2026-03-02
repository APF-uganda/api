from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from authentication.permissions import IsAuthenticated, IsAdmin
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .services.analytics_coordinator import analytics_coordinator
from .services.generator import ReportGenerator
from .models import ReportTemplate, GeneratedReport
from .serializers import ReportTemplateSerializer, GeneratedReportSerializer

#   DASHBOARD VIEWS ---

class DashboardSummaryAPIView(APIView):
    """Unified dashboard summary supporting time periods"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Get unified dashboard summary with membership, applications, and system metrics for specified time period",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period for analytics (default: 30d)",
                type=openapi.TYPE_STRING,
                enum=['7d', '30d', '90d', '1y'],
                default='30d'
            ),
        ],
        responses={
            200: openapi.Response(
                description="Dashboard summary with trends and metrics",
                examples={
                    "application/json": {
                        "membership": {
                            "total_members": 32,
                            "growth": {
                                "labels": ["Mar 01", "Mar 02"],
                                "data": [30, 32]
                            }
                        },
                        "applications": {
                            "total_applications": 45,
                            "status_breakdown": {
                                "labels": ["Pending", "Approved", "Rejected"],
                                "data": [12, 28, 5]
                            }
                        },
                        "system": {
                            "active_users_30d": 25,
                            "daily_activity": {
                                "labels": ["Mar 01", "Mar 02"],
                                "data": [15, 18]
                            }
                        }
                    }
                }
            )
        }
    )
    def get(self, request):
        period = request.query_params.get('period', '30d')
        try:
            raw_data = analytics_coordinator.get_dashboard_summary(period)
            trends = raw_data.get('trends', {})
            metrics = raw_data.get('key_metrics', {})
            
            def safe_chart(key, default_labels=None):
                chart = trends.get(key, {})
                labels = chart.get('labels', [])
                data = chart.get('data', [])
                if not labels or not data:
                    return {
                        "labels": default_labels or [timezone.now().strftime('%b %d')],
                        "data": [0]
                    }
                return {"labels": labels, "data": data}

            return Response({
                "membership": {
                    "total_members": metrics.get('total_members', 0),
                    "growth": safe_chart('membership_growth')
                },
                "applications": {
                    "total_applications": metrics.get('total_applications', 0),
                    "status_breakdown": safe_chart('application_status', ["Pending", "Approved", "Rejected"])
                },
                "system": {
                    "active_users_30d": metrics.get('active_users_30d', 0),
                    "daily_activity": safe_chart('daily_activity')
                }
            })
        except Exception:
            empty = {"labels": [timezone.now().strftime('%b %d')], "data": [0]}
            return Response({
                "membership": {"total_members": 0, "growth": empty},
                "applications": {"total_applications": 0, "status_breakdown": empty},
                "system": {"active_users_30d": 0, "daily_activity": empty}
            }, status=200)

class ChartDataAPIView(APIView):
    """General endpoint for individual chart components"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Get data for individual chart components",
        manual_parameters=[
            openapi.Parameter(
                'type',
                openapi.IN_QUERY,
                description="Type of chart data to retrieve",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period for chart data (default: 30d)",
                type=openapi.TYPE_STRING,
                enum=['7d', '30d', '90d', '1y'],
                default='30d'
            ),
        ],
        responses={
            200: openapi.Response(
                description="Chart data with labels and values",
                examples={
                    "application/json": {
                        "labels": ["Mar 01", "Mar 02"],
                        "data": [15, 18]
                    }
                }
            )
        }
    )
    def get(self, request):
        chart_type = request.query_params.get('type')
        period = request.query_params.get('period', '30d')
        try:
            data = analytics_coordinator.get_chart_data(chart_type, period)
            if not data or not data.get('labels'):
                return Response({"labels": [timezone.now().strftime('%b %d')], "data": [0]})
            return Response(data)
        except Exception:
            return Response({"labels": [timezone.now().strftime('%b %d')], "data": [0]})



class AnalyticsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Get comprehensive analytics across all services",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period for analytics (default: 30d)",
                type=openapi.TYPE_STRING,
                enum=['7d', '30d', '90d', '1y'],
                default='30d'
            ),
        ],
        responses={
            200: "Comprehensive analytics data"
        }
    )
    def get(self, request):
        period = request.query_params.get('period', '30d')
        return Response(analytics_coordinator.get_comprehensive_analytics(period))

class MembershipAnalyticsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Get membership-specific analytics and metrics",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period for analytics (default: 30d)",
                type=openapi.TYPE_STRING,
                enum=['7d', '30d', '90d', '1y'],
                default='30d'
            ),
        ],
        responses={
            200: "Membership analytics data"
        }
    )
    def get(self, request):
        period = request.query_params.get('period', '30d')
        return Response(analytics_coordinator.get_service_metrics('membership', period))

class ApplicationAnalyticsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Get application-specific analytics and metrics",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period for analytics (default: 30d)",
                type=openapi.TYPE_STRING,
                enum=['7d', '30d', '90d', '1y'],
                default='30d'
            ),
        ],
        responses={
            200: "Application analytics data"
        }
    )
    def get(self, request):
        period = request.query_params.get('period', '30d')
        return Response(analytics_coordinator.get_service_metrics('applications', period))

class SystemAnalyticsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Get system-wide analytics and metrics",
        manual_parameters=[
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Time period for analytics (default: 30d)",
                type=openapi.TYPE_STRING,
                enum=['7d', '30d', '90d', '1y'],
                default='30d'
            ),
        ],
        responses={
            200: "System analytics data"
        }
    )
    def get(self, request):
        period = request.query_params.get('period', '30d')
        return Response(analytics_coordinator.get_service_metrics('system', period))



class AvailableChartsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Get list of all available chart types",
        responses={
            200: openapi.Response(
                description="List of available charts",
                examples={
                    "application/json": {
                        "charts": [
                            "membership_growth",
                            "application_status",
                            "daily_activity",
                            "revenue_trends"
                        ]
                    }
                }
            )
        }
    )
    def get(self, request):
        return Response(analytics_coordinator.get_available_charts())

class AnalyticsHealthCheckAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Check health status of analytics services",
        responses={
            200: openapi.Response(
                description="Health check status",
                examples={
                    "application/json": {
                        "status": "healthy",
                        "services": {
                            "analytics_coordinator": "ok",
                            "cache": "ok"
                        }
                    }
                }
            )
        }
    )
    def get(self, request):
        return Response(analytics_coordinator.health_check())

class CacheManagementsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Clear analytics cache",
        responses={
            200: openapi.Response(
                description="Cache cleared successfully",
                examples={
                    "application/json": {
                        "message": "Cache cleared successfully"
                    }
                }
            )
        }
    )
    def post(self, request):
        analytics_coordinator.clear_cache()
        return Response({"message": "Cache cleared successfully"})



class ReportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ReportTemplateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = ReportTemplate.objects.filter(is_active=True).order_by('-created_at')

    @swagger_auto_schema(tags=["reports"], operation_description="List all report templates")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["reports"], operation_description="Retrieve a report template by ID")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["reports"], operation_description="Create a new report template")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["reports"], operation_description="Update a report template")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["reports"], operation_description="Partially update a report template")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["reports"], operation_description="Delete a report template")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class GeneratedReportViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = GeneratedReport.objects.all().order_by('-created_at')

    @swagger_auto_schema(tags=["reports"], operation_description="List all generated reports")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["reports"], operation_description="Retrieve a generated report by ID")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["reports"], operation_description="Generate a new report")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save(
            generated_by=self.request.user,
            status='processing',
            processing_started_at=timezone.now()
        )
        try:
            generator = ReportGenerator(instance)
            generator.execute()
        except Exception:
            instance.status = 'failed'
            instance.save()


class DownloadReportAPIView(APIView):
    """Download a generated report file"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        tags=["reports"],
        operation_description="Download a generated report file",
        responses={
            200: openapi.Response(
                description="Report file download",
                schema=openapi.Schema(
                    type=openapi.TYPE_FILE
                )
            ),
            400: "Report is not ready for download",
            404: "Report not found"
        }
    )
    def get(self, request, report_id):
        from django.http import FileResponse, Http404
        import os
        from django.conf import settings
        
        try:
            report = GeneratedReport.objects.get(id=report_id)
            
            if report.status != 'completed':
                return Response(
                    {'error': 'Report is not ready for download', 'status': report.status},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not report.file_path:
                return Response(
                    {'error': 'Report file not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            file_path = os.path.join(settings.MEDIA_ROOT, report.file_path)
            
            if not os.path.exists(file_path):
                return Response(
                    {'error': 'Report file does not exist on server'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update download tracking
            report.download_count += 1
            report.last_downloaded_at = timezone.now()
            report.save(update_fields=['download_count', 'last_downloaded_at'])
            
            # Serve the file
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
            
        except GeneratedReport.DoesNotExist:
            return Response(
                {'error': 'Report not found'},
                status=status.HTTP_404_NOT_FOUND
            )