from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ForumPostViewSet, CommentViewSet, LikeViewSet,
    CategoryViewSet, TagViewSet, ReportViewSet
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'posts', ForumPostViewSet, basename='forum-post')
router.register(r'comments', CommentViewSet, basename='forum-comment')
router.register(r'likes', LikeViewSet, basename='forum-like')
router.register(r'categories', CategoryViewSet, basename='forum-category')
router.register(r'tags', TagViewSet, basename='forum-tag')
router.register(r'reports', ReportViewSet, basename='forum-report')

urlpatterns = [
    path('', include(router.urls)),
]
