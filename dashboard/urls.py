from django.urls import path
from .views import (
    TotalApplicationView,
    TotalMemberView,
    ApplicationStatisticsView,
    RecentApplicationsView,
    RecentPaymentsView,
    MemberDashboardView,
)

urlpatterns = [
    path('total-applications/', TotalApplicationView.as_view()),
    path('total-members/', TotalMemberView.as_view()),
    path('statistics/', ApplicationStatisticsView.as_view()),
    path('recent-applications/', RecentApplicationsView.as_view()),
    path('recent-payments/', RecentPaymentsView.as_view()),
    path('member/dashboard/', MemberDashboardView.as_view()),
]
