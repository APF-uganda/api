from django.shortcuts import render
from .services import (
    get_total_applications,
    get_total_members,
    get_application_statistics,
    get_recent_applications,
    get_recent_payments,
    get_member_dashboard_data,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import (
    TotalApplicationSerializer,
    TotalMemberSerializer,
    ApplicationStatisticsSerializer,
    MemberDashboardSerializer,
    DashboardApplicationSerializer,
)
from authentication.permissions import IsAuthenticated, IsAdmin, IsMember
from drf_yasg.utils import swagger_auto_schema
from applications.serializers import ApplicationSerializer

from rest_framework.permissions import AllowAny


class TotalApplicationView(APIView):
    # permission_classes = [IsAuthenticated, IsAdmin]
    permission_classes = [AllowAny]
    @swagger_auto_schema(tags=["dashboard"])
    def get(self, request):
        data = {
            "total_applications": get_total_applications()
        }
        serializer = TotalApplicationSerializer(data)

        return Response(serializer.data)

class TotalMemberView(APIView):
    #  permission_classes = [IsAuthenticated, IsAdmin]
     permission_classes = [AllowAny]
     @swagger_auto_schema(tags=["dashboard"])
     def get(self, request):
         data ={
             "total_members": get_total_members()
         }
         serializer = TotalMemberSerializer(data)

         return Response(serializer.data)

class ApplicationStatisticsView(APIView):
    """Enhanced statistics endpoint for admin dashboard."""
    permission_classes = [AllowAny]  # TODO: Change to [IsAuthenticated, IsAdmin] in production
    
    @swagger_auto_schema(tags=["dashboard"])
    def get(self, request):
        data = get_application_statistics()
        serializer = ApplicationStatisticsSerializer(data)
        return Response(serializer.data)



class RecentApplicationsView(APIView):
    """Get recent applications for dashboard display."""
    permission_classes = [AllowAny]  # TODO: Change to IsAdmin in production
    
    @swagger_auto_schema(tags=["dashboard"])
    def get(self, request):
        limit = int(request.query_params.get('limit', 5))
        applications = get_recent_applications(limit)
        serializer = DashboardApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class RecentPaymentsView(APIView):
    """Get recent successful payments for dashboard display."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(tags=["dashboard"])
    def get(self, request):
        limit = int(request.query_params.get('limit', 5))
        payments = get_recent_payments(limit)
        return Response(payments)

@swagger_auto_schema(tags=["dashboard"])
class MemberDashboardView(APIView):
    """Get member dashboard data."""
    permission_classes = [IsAuthenticated, IsMember]

    @swagger_auto_schema(tags=["dashboard"])
    def get(self, request):
        data = get_member_dashboard_data(request.user, request=request)
        serializer = MemberDashboardSerializer(data)
        return Response(serializer.data)


