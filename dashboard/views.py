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
from drf_yasg import openapi
from applications.serializers import ApplicationSerializer

from rest_framework.permissions import AllowAny


class TotalApplicationView(APIView):
    # permission_classes = [IsAuthenticated, IsAdmin]
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        tags=["dashboard"],
        operation_description="Get total number of applications in the system",
        responses={
            200: openapi.Response(
                description="Total applications count",
                schema=TotalApplicationSerializer,
                examples={
                    "application/json": {
                        "total_applications": 45
                    }
                }
            )
        }
    )
    def get(self, request):
        data = {
            "total_applications": get_total_applications()
        }
        serializer = TotalApplicationSerializer(data)

        return Response(serializer.data)

class TotalMemberView(APIView):
    #  permission_classes = [IsAuthenticated, IsAdmin]
     permission_classes = [AllowAny]
     
     @swagger_auto_schema(
        tags=["dashboard"],
        operation_description="Get total number of members in the system",
        responses={
            200: openapi.Response(
                description="Total members count",
                schema=TotalMemberSerializer,
                examples={
                    "application/json": {
                        "total_members": 32
                    }
                }
            )
        }
    )
     def get(self, request):
         data ={
             "total_members": get_total_members()
         }
         serializer = TotalMemberSerializer(data)

         return Response(serializer.data)

class ApplicationStatisticsView(APIView):
    """Enhanced statistics endpoint for admin dashboard."""
    permission_classes = [AllowAny]  # TODO: Change to [IsAuthenticated, IsAdmin] in production
    
    @swagger_auto_schema(
        tags=["dashboard"],
        operation_description="Get comprehensive application statistics including totals, status breakdown, and trends",
        responses={
            200: openapi.Response(
                description="Application statistics with trends",
                schema=ApplicationStatisticsSerializer,
                examples={
                    "application/json": {
                        "total_applications": 45,
                        "pending_applications": 12,
                        "approved_applications": 28,
                        "rejected_applications": 5,
                        "paid_applications": 25,
                        "total_revenue": 1250000.00,
                        "trends": {
                            "total_change": 15.5,
                            "pending_change": 8.2,
                            "approved_change": 12.3,
                            "rejected_change": -2.1,
                            "paid_change": 18.7,
                            "revenue_change": 22.4
                        }
                    }
                }
            )
        }
    )
    def get(self, request):
        data = get_application_statistics()
        serializer = ApplicationStatisticsSerializer(data)
        return Response(serializer.data)



class RecentApplicationsView(APIView):
    """Get recent applications for dashboard display."""
    permission_classes = [AllowAny]  # TODO: Change to IsAdmin in production
    
    @swagger_auto_schema(
        tags=["dashboard"],
        operation_description="Get recent applications for dashboard display",
        manual_parameters=[
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Number of recent applications to return (default: 5)",
                type=openapi.TYPE_INTEGER,
                default=5
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of recent applications",
                schema=DashboardApplicationSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "id": 45,
                            "username": "Eric",
                            "email": "ericmhwz@gmail.com",
                            "first_name": "Eric",
                            "last_name": "Muhwezi",
                            "status": "pending",
                            "payment_status": "idle",
                            "submitted_at": "2026-03-02T14:27:30.002748+03:00",
                            "updated_at": "2026-03-02T14:27:30.002788+03:00"
                        }
                    ]
                }
            )
        }
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 5))
        applications = get_recent_applications(limit)
        serializer = DashboardApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class RecentPaymentsView(APIView):
    """Get recent successful payments for dashboard display."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        tags=["dashboard"],
        operation_description="Get recent successful payments for dashboard display",
        manual_parameters=[
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Number of recent payments to return (default: 5)",
                type=openapi.TYPE_INTEGER,
                default=5
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of recent payments",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "application_id": 45,
                            "amount": "50000.00",
                            "payment_method": "mtn",
                            "status": "completed",
                            "transaction_reference": "TXN123456",
                            "created_at": "2026-03-02T14:27:30.002748+03:00"
                        }
                    ]
                }
            )
        }
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 5))
        payments = get_recent_payments(limit)
        return Response(payments)

class MemberDashboardView(APIView):
    """Get member dashboard data."""
    permission_classes = [IsAuthenticated, IsMember]

    @swagger_auto_schema(
        tags=["dashboard"],
        operation_description="Get comprehensive dashboard data for authenticated member including profile, documents, activity, and notifications",
        responses={
            200: openapi.Response(
                description="Member dashboard data",
                schema=MemberDashboardSerializer,
                examples={
                    "application/json": {
                        "profile": {
                            "display_name": "Eric Muhwezi",
                            "membership_category": "Full Member",
                            "membership_status": "active",
                            "member_since": "2026-01-15",
                            "next_renewal_date": "2027-01-15"
                        },
                        "documents": [],
                        "recent_activity": [],
                        "notifications": []
                    }
                }
            ),
            401: "Authentication required"
        }
    )
    def get(self, request):
        data = get_member_dashboard_data(request.user, request=request)
        serializer = MemberDashboardSerializer(data)
        return Response(serializer.data)


