from rest_framework import serializers
from django.db.models import Count, Q
from .models import ForumPost, Comment, Like, Category, Tag, Report, PostView


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for forum categories
    """
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'post_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_post_count(self, obj):
        """Get the number of published posts in this category"""
        return obj.posts.filter(status='published').count()


class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for forum tags
    """
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'created_at']


class AuthorSerializer(serializers.Serializer):
    """
    Simplified serializer for post authors
    """
    id = serializers.IntegerField()
    email = serializers.EmailField()
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    full_name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        """Get full name from first and last name"""
        first = getattr(obj, 'first_name', '')
        last = getattr(obj, 'last_name', '')
        full = f"{first} {last}".strip()
        return full if full else obj.email.split('@')[0]

    def get_initials(self, obj):
        """Generate initials from first and last name"""
        first = getattr(obj, 'first_name', '')
        last = getattr(obj, 'last_name', '')
        
        if first and last:
            return f"{first[0]}{last[0]}".upper()
        elif first:
            return first[0].upper()
        elif last:
            return last[0].upper()
        else:
            # Use first letter of email if no name
            email = getattr(obj, 'email', '')
            return email[0].upper() if email else 'U'

    def get_profile_picture_url(self, obj):
        """Get absolute profile picture URL if available"""
        profile_picture = getattr(obj, 'profile_picture', None)
        if profile_picture:
            try:
                url = profile_picture.url
            except Exception:
                url = None
            else:
                request = self.context.get('request')
                return request.build_absolute_uri(url) if request else url

        profile = getattr(obj, 'profile', None)
        if profile:
            try:
                url = profile.get_profile_picture_url()
            except Exception:
                url = None
            if url:
                request = self.context.get('request')
                return request.build_absolute_uri(url) if request else url

        return None


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for forum comments
    """
    author = AuthorSerializer(read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'content', 
            'parent', 'is_edited', 'reply_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_edited', 'created_at', 'updated_at']

    def get_reply_count(self, obj):
        """Get the number of replies to this comment"""
        return obj.replies.count()


class LikeSerializer(serializers.ModelSerializer):
    """
    Serializer for forum post likes
    """
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'post', 'user', 'created_at']
        read_only_fields = ['id', 'created_at']


class ForumPostListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing forum posts
    """
    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()
    viewers = serializers.SerializerMethodField()

    class Meta:
        model = ForumPost
        fields = [
            'id', 'title', 'content', 'author', 'category', 'tags',
            'status', 'views_count', 'comment_count', 'like_count', 'viewers',
            'is_pinned', 'is_locked', 'is_liked',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'views_count', 'created_at', 'updated_at']

    def get_comment_count(self, obj):
        """Get comment count excluding the author's own comments"""
        return getattr(obj, 'comments_total', obj.replies_count_excluding_author)

    def get_like_count(self, obj):
        """Get like count from annotation or calculate"""
        return getattr(obj, 'likes_total', obj.like_count)

    def get_is_liked(self, obj):
        """Check if the current user has liked this post"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return Like.objects.filter(post=obj, user=request.user).exists()
        return False

    def get_views_count(self, obj):
        """Get view count excluding the author's own view"""
        return PostView.objects.filter(post=obj).exclude(user=obj.author).count()

    def get_viewers(self, obj):
        """Get recent viewers for display"""
        views = (
            PostView.objects.filter(post=obj)
            .exclude(user=obj.author)
            .select_related('user')
            .order_by('-created_at')[:5]
        )
        return [AuthorSerializer(view.user, context=self.context).data for view in views]


class ForumPostDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a single forum post
    """
    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        source='tags',
        write_only=True,
        required=False
    )
    comments = CommentSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()
    viewers = serializers.SerializerMethodField()

    class Meta:
        model = ForumPost
        fields = [
            'id', 'title', 'content', 
            'author', 'category', 'category_id',
            'tags', 'tag_ids',
            'status', 'views_count', 
            'comment_count', 'like_count', 'viewers',
            'is_pinned', 'is_locked', 'is_liked',
            'comments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'views_count', 'created_at', 'updated_at']

    def get_is_liked(self, obj):
        """Check if the current user has liked this post"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return Like.objects.filter(post=obj, user=request.user).exists()
        return False

    def get_comment_count(self, obj):
        """Get comment count excluding the author's own comments"""
        return getattr(obj, 'comments_total', obj.replies_count_excluding_author)

    def get_like_count(self, obj):
        """Get like count from annotation or calculate"""
        return getattr(obj, 'likes_total', obj.like_count)

    def get_views_count(self, obj):
        """Get view count excluding the author's own view"""
        return PostView.objects.filter(post=obj).exclude(user=obj.author).count()

    def get_viewers(self, obj):
        """Get recent viewers for display"""
        views = (
            PostView.objects.filter(post=obj)
            .exclude(user=obj.author)
            .select_related('user')
            .order_by('-created_at')[:5]
        )
        return [AuthorSerializer(view.user, context=self.context).data for view in views]

    def validate_title(self, value):
        """Validate post title"""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Title must be at least 10 characters long.")
        if len(value) > 255:
            raise serializers.ValidationError("Title must not exceed 255 characters.")
        return value.strip()

    def validate_content(self, value):
        """Validate post content"""
        if not value or len(value.strip()) < 20:
            raise serializers.ValidationError("Content must be at least 20 characters long.")
        return value.strip()


class ReportSerializer(serializers.ModelSerializer):
    """
    Serializer for content reports
    """
    reporter = AuthorSerializer(read_only=True)
    post = ForumPostListSerializer(read_only=True)
    reviewed_by = AuthorSerializer(read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'post',
            'reporter',
            'reason', 'description', 'status',
            'reviewed_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_description(self, value):
        """Validate report description"""
        if value and len(value) > 1000:
            raise serializers.ValidationError("Description must not exceed 1000 characters.")
        return value.strip() if value else ""


class ForumStatsSerializer(serializers.Serializer):
    """
    Serializer for forum statistics
    """
    total_posts = serializers.IntegerField()
    published_posts = serializers.IntegerField()
    draft_posts = serializers.IntegerField()
    reported_posts = serializers.IntegerField()
    total_comments = serializers.IntegerField()
    total_likes = serializers.IntegerField()
    active_users = serializers.IntegerField()
    pending_reports = serializers.IntegerField()
