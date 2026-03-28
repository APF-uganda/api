import os
from django.utils import timezone
from django.conf import settings
from django.http import FileResponse

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view
from rest_framework_simplejwt.authentication import JWTAuthentication

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from authentication.permissions import IsAuthenticated, IsAdmin
from .models import ReportTemplate, GeneratedReport
from .services.analytics_coordinator import analytics_coordinator
from .services.generator import ReportGenerator
from .serializers import ReportTemplateSerializer, GeneratedReportSerializer

# DASHBOARD VIEWS

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
        responses={200: "Dashboard summary with trends and metrics"}
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
                },
                "key_metrics": {
                    "total_members": metrics.get('total_members', 0),
                    "total_applications": metrics.get('total_applications', 0),
                    "pending_applications": metrics.get('pending_applications', 0),
                    "active_users_30d": metrics.get('active_users_30d', 0),
                    "total_revenue": metrics.get('total_revenue', 0),
                    "revenue_growth_rate": metrics.get('revenue_growth_rate', 0),
                    "pending_payments": metrics.get('pending_payments', 0)
                }
            })
        except Exception:
            empty = {"labels": [timezone.now().strftime('%b %d')], "data": [0]}
            return Response({
                "membership": {"total_members": 0, "growth": empty},
                "applications": {"total_applications": 0, "status_breakdown": empty},
                "system": {"active_users_30d": 0, "daily_activity": empty},
                "key_metrics": {
                    "total_members": 0, "total_applications": 0, "pending_applications": 0,
                    "active_users_30d": 0, "total_revenue": 0, "revenue_growth_rate": 0, "pending_payments": 0
                }
            }, status=200)

class ChartDataAPIView(APIView):
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

# 

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

    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """Action for DELETE /api/v1/reports/generated-reports/{id}/delete/"""
        report = self.get_object()
        try:
            if report.file_path:
                full_path = os.path.join(settings.MEDIA_ROOT, report.file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            report.delete()
            return Response({"message": "Report deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        filters = self.request.data.get('filters', {})
        instance = serializer.save(
            generated_by=self.request.user,
            status='processing',
            filters_applied=filters, 
            processing_started_at=timezone.now()
        )
        try:
            generator = ReportGenerator(instance)
            generator.execute()
        except Exception as e:
            instance.status = 'failed'
            instance.error_message = str(e)
            instance.save()

#  DOWNLOAD ACTIONS 

class DownloadReportAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, report_id):
        try:
            report = GeneratedReport.objects.get(id=report_id)
            if report.status != 'completed' or not report.file_path:
                return Response({'error': 'Report not ready'}, status=status.HTTP_400_BAD_REQUEST)
            
            file_path = os.path.join(settings.MEDIA_ROOT, report.file_path)
            if not os.path.exists(file_path):
                return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
            
            report.download_count += 1
            report.last_downloaded_at = timezone.now()
            report.save(update_fields=['download_count', 'last_downloaded_at'])
            
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
        except GeneratedReport.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
def delete_generated_report(request, report_id):
    """Standalone fallback delete endpoint"""
    try:
        report = GeneratedReport.objects.get(id=report_id)
        if report.file_path:
            full_path = os.path.join(settings.MEDIA_ROOT, report.file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        report.delete()
        return Response({"message": "Report deleted successfully"}, status=status.HTTP_200_OK)
    except GeneratedReport.DoesNotExist:
        return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)