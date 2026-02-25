from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from authentication.permissions import IsAuthenticated, IsAdmin

from .services.analytics_coordinator import analytics_coordinator
from .services.generator import ReportGenerator
from .models import ReportTemplate, GeneratedReport
from .serializers import ReportTemplateSerializer, GeneratedReportSerializer

#   DASHBOARD VIEWS ---

class DashboardSummaryAPIView(APIView):
    """Unified dashboard summary supporting time periods"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

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
    def get(self, request):
        period = request.query_params.get('period', '30d')
        return Response(analytics_coordinator.get_comprehensive_analytics(period))

class MembershipAnalyticsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    def get(self, request):
        period = request.query_params.get('period', '30d')
        return Response(analytics_coordinator.get_service_metrics('membership', period))

class ApplicationAnalyticsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    def get(self, request):
        period = request.query_params.get('period', '30d')
        return Response(analytics_coordinator.get_service_metrics('applications', period))

class SystemAnalyticsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    def get(self, request):
        period = request.query_params.get('period', '30d')
        return Response(analytics_coordinator.get_service_metrics('system', period))



class AvailableChartsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    def get(self, request):
        return Response(analytics_coordinator.get_available_charts())

class AnalyticsHealthCheckAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    def get(self, request):
        return Response(analytics_coordinator.health_check())

class CacheManagementsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    def post(self, request):
        analytics_coordinator.clear_cache()
        return Response({"message": "Cache cleared successfully"})



class ReportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ReportTemplateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = ReportTemplate.objects.filter(is_active=True).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class GeneratedReportViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = GeneratedReport.objects.all().order_by('-created_at')

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