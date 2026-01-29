from django.urls import path
from .views import TotalApplicationView,TotalMemberView

urlpatterns = [
    path('total-applications/', TotalApplicationView.as_view()),
    path('total-members/', TotalMemberView.as_view())
]