from django.urls import path
from .views import TotalApplicationView

urlpatterns = [
    path('total-applications/', TotalApplicationView.as_view())
]