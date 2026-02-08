from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.db.models import Prefetch, Count, Q, Max
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import ForumPost, Comment, Like, Category, Tag, Report, PostView
from .serializers import (
    ForumPostListSerializer, ForumPostDetailSerializer,
    CommentSerializer, LikeSerializer, CategorySerializer,
    TagSerializer, ReportSerializer, ForumStatsSerializer,
    AuthorSerializer
)
from rest_framework.pagination import PageNumberPagination



class ForumPostPagination(PageNumberPagination):
    """
    Pagination class for forum posts
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing forum categories
    CRUD operations for categories
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        """Optimize query with post counts"""
        return Category.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        )


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing forum tags
    CRUD operations for tags
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ForumPostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing forum posts
    Provides CRUD operations, filtering, and statistics
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = ForumPostPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'author__email', 'author__first_name', 'author__last_name']
    ordering_fields = ['created_at', 'updated_at', 'views_count', 'comments_total', 'likes_total']
    ordering = ['-is_pinned', '-created_at']

    def get_queryset(self):
        """
        Optimize queries with prefetch (without annotations to avoid setter issues)
        """
        queryset = ForumPost.objects.select_related(
            'author', 'category'
        ).prefetch_related(
            'tags',
            Prefetch('comments', queryset=Comment.objects.select_related('author')),
            Prefetch('likes', queryset=Like.objects.select_related('user'))
        )

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by category
        category_slug = self.request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Filter by tag
        tag_slug = self.request.query_params.get('tag', None)
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        # Filter by author
        author_id = self.request.query_params.get('author', None)
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        # Only distinct when tag filter is used to avoid DB errors with ordering
        if tag_slug:
            queryset = queryset.distinct()

        queryset = queryset.annotate(
            likes_total=Count('likes', distinct=True),
            comments_total=Count('comments', distinct=True)
        )
        return queryset

    def get_serializer_class(self):
        """
        Use different serializers for list and detail views
        """
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return ForumPostDetailSerializer
        return ForumPostListSerializer

    def list(self, request, *args, **kwargs):
        """
        List forum posts with error handling
        """
        print("\n" + "="*50)
        print("LIST POSTS REQUEST")
        print("="*50)
        print(f"User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        print(f"Query params: {request.query_params}")
        print("="*50 + "\n")
        
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            print(f"\n ERROR in list():")
            print(f"   Type: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            import traceback
            traceback.print_exc()
            print("\n")
            raise

    def retrieve(self, request, *args, **kwargs):
        """
        Record a unique view when post is retrieved
        """
        instance = self.get_object()
        if request.user.is_authenticated and request.user != instance.author:
          PostView.objects.get_or_create(post=instance, user=request.user)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new forum post with detailed logging
        """
        print("\n" + "="*50)
        print(" CREATE POST REQUEST")
        print("="*50)
        print(f"User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        print(f"Data received: {request.data}")
        print("="*50 + "\n")
        
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            print(f"\n ERROR in create():")
            print(f"   Type: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            import traceback
            traceback.print_exc()
            print("\n")
            raise

    def perform_create(self, serializer):
        """
        Set the author to the current user when creating a post
        """
        try:
            post = serializer.save(author=self.request.user)
            print(f" Post created successfully: {post.title} by {post.author.email}")
        except Exception as e:
            print(f" Error creating post: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_posts(self, request):
        """
        Get posts created by the current user
        """
        posts = self.get_queryset().filter(author=request.user)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """
        Like a post
        """
        post = self.get_object()
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        
        if not created:
            return Response(
                {'message': 'You have already liked this post'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {'message': 'Post liked successfully', 'like_count': post.like_count},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def viewers(self, request, pk=None):
        """
        Get full list of viewers for a post (excluding author)
        """
        post = self.get_object()
        views = (
            PostView.objects.filter(post=post)
            .exclude(user=post.author)
            .select_related('user')
            .order_by('-created_at')
        )
        data = [AuthorSerializer(view.user, context={'request': request}).data for view in views]
        return Response(data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, pk=None):
        """
        Unlike a post
        """
        post = self.get_object()
        deleted, _ = Like.objects.filter(post=post, user=request.user).delete()
        
        if not deleted:
            return Response(
                {'message': 'You have not liked this post'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {'message': 'Post unliked successfully', 'like_count': post.like_count},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_pin(self, request, pk=None):
        """
        Toggle pin status of a post (admin only)
        """
        if not request.user.is_staff:
            return Response(
                {'message': 'Only admins can pin posts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        post = self.get_object()
        post.is_pinned = not post.is_pinned
        post.save(update_fields=['is_pinned'])
        
        return Response(
            {'message': f'Post {"pinned" if post.is_pinned else "unpinned"} successfully'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_lock(self, request, pk=None):
        """
        Toggle lock status of a post (admin only)
        """
        if not request.user.is_staff:
            return Response(
                {'message': 'Only admins can lock posts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        post = self.get_object()
        post.is_locked = not post.is_locked
        post.save(update_fields=['is_locked'])
        
        return Response(
            {'message': f'Post {"locked" if post.is_locked else "unlocked"} successfully'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get forum statistics
        """
        # Calculate date range for active users (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)

        # Get all posts and calculate stats
        all_posts = ForumPost.objects.all()
        
        stats = {
            'total_posts': all_posts.count(),
            'published_posts': all_posts.filter(status='published').count(),
            'draft_posts': all_posts.filter(status='draft').count(),
            'reported_posts': all_posts.filter(status='reported').count(),
            'total_comments': Comment.objects.count(),
            'total_likes': Like.objects.count(),
            'active_users': all_posts.filter(
                created_at__gte=thirty_days_ago
            ).values('author').distinct().count(),
            'pending_reports': Report.objects.filter(status='pending').count(),
        }
        
        serializer = ForumStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active_users(self, request):
        """
        Get active forum users based on recent post/comment activity
        """
        User = get_user_model()
        now = timezone.now()
        current_user_id = request.user.id if request.user.is_authenticated else None

        post_activity = (
            ForumPost.objects.values('author')
            .annotate(last_active=Max('created_at'))
        )
        comment_activity = (
            Comment.objects.values('author')
            .annotate(last_active=Max('created_at'))
        )

        last_seen_map = {}
        for item in post_activity:
            last_seen_map[item['author']] = item['last_active']
        for item in comment_activity:
            existing = last_seen_map.get(item['author'])
            if not existing or (item['last_active'] and item['last_active'] > existing):
                last_seen_map[item['author']] = item['last_active']

        user_ids = [uid for uid, ts in last_seen_map.items() if ts]
        if current_user_id is not None:
            user_ids = [uid for uid in user_ids if uid != current_user_id]
        users = User.objects.filter(id__in=user_ids)

        results = []
        for user in users:
            last_active = last_seen_map.get(user.id)
            if not last_active:
                continue
            delta = now - last_active
            if delta <= timedelta(minutes=5):
                status = 'online'
            elif delta <= timedelta(hours=1):
                status = 'away'
            else:
                status = 'offline'
            author_data = AuthorSerializer(user, context={'request': request}).data
            results.append({
                'name': author_data.get('full_name') or author_data.get('email') or 'Member',
                'initials': author_data.get('initials') or 'U',
                'profile_picture_url': author_data.get('profile_picture_url'),
                'status': status,
                'last_seen': last_active.isoformat()
            })

        results.sort(key=lambda x: x['last_seen'], reverse=True)
        return Response(results[:10])


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments
    """
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['created_at']

    def get_queryset(self):
        """
        Filter comments by post if provided
        """
        queryset = Comment.objects.select_related('author', 'post').prefetch_related('replies')

        post_id = self.request.query_params.get('post', None)
        if post_id:
            queryset = queryset.filter(post_id=post_id)

        # Filter top-level comments (no parent)
        parent_only = self.request.query_params.get('parent_only', None)
        if parent_only == 'true':
            queryset = queryset.filter(parent__isnull=True)

        return queryset

    def perform_create(self, serializer):
        """
        Set the author to the current user when creating a comment
        """
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """
        Mark comment as edited when updated
        """
        serializer.save(is_edited=True)


class LikeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing likes (read-only)
    Use ForumPost like/unlike actions to create/delete likes
    """
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Filter likes by post if provided
        """
        queryset = Like.objects.select_related('user', 'post')

        post_id = self.request.query_params.get('post', None)
        if post_id:
            queryset = queryset.filter(post_id=post_id)

        return queryset


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing content reports
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Admins see all reports, users see only their own
        """
        queryset = Report.objects.select_related(
            'post', 'reporter', 'reviewed_by'
        ).prefetch_related('post__author')

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Admins see all, users see only their reports
        if not self.request.user.is_staff:
            queryset = queryset.filter(reporter=self.request.user)

        return queryset

    def perform_create(self, serializer):
        """
        Set the reporter to the current user
        """
        serializer.save(reporter=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def review(self, request, pk=None):
        """
        Mark a report as reviewed (admin only)
        """
        if not request.user.is_staff:
            return Response(
                {'message': 'Only admins can review reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        report = self.get_object()
        report.status = 'reviewed'
        report.reviewed_by = request.user
        report.save(update_fields=['status', 'reviewed_by', 'updated_at'])
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def resolve(self, request, pk=None):
        """
        Resolve a report (admin only)
        """
        if not request.user.is_staff:
            return Response(
                {'message': 'Only admins can resolve reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        report = self.get_object()
        report.status = 'resolved'
        report.reviewed_by = request.user
        
        # Update the post status to reported
        post = report.post
        post.status = 'reported'
        post.save(update_fields=['status'])
        
        report.save(update_fields=['status', 'reviewed_by', 'updated_at'])
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def dismiss(self, request, pk=None):
        """
        Dismiss a report (admin only)
        """
        if not request.user.is_staff:
            return Response(
                {'message': 'Only admins can dismiss reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        report = self.get_object()
        report.status = 'dismissed'
        report.reviewed_by = request.user
        report.save(update_fields=['status', 'reviewed_by', 'updated_at'])
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)
