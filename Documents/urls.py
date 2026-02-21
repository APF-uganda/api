from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, get_member_documents


router = DefaultRouter()
router.register(r'', DocumentViewSet, basename='document')

urlpatterns = [
    path('member-documents/<int:user_id>/', get_member_documents, name='member-documents'),
    path('', include(router.urls)),
]
