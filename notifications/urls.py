from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, UserNotificationViewSet, AnnouncementViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'user-notifications', UserNotificationViewSet, basename='user-notification')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')

urlpatterns = router.urls