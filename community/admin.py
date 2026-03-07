from django.contrib import admin
from .models import ForumPost, Comment, Like, Category, Tag, Report


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for forum categories
    """
    list_display = ['name', 'slug', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Admin interface for forum tags
    """
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    """
    Admin interface for forum posts
    """
    list_display = ['title', 'author', 'category', 'status', 'views_count', 'is_pinned', 'is_locked', 'created_at']
    list_filter = ['status', 'category', 'is_pinned', 'is_locked', 'created_at']
    search_fields = ['title', 'content', 'author__email', 'author__first_name', 'author__last_name']
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    filter_horizontal = ['tags']
    date_hierarchy = 'created_at'
    ordering = ['-is_pinned', '-created_at']

    fieldsets = (
        ('Post Information', {
            'fields': ('title', 'content', 'author', 'category', 'tags')
        }),
        ('Status & Settings', {
            'fields': ('status', 'is_pinned', 'is_locked')
        }),
        ('Statistics', {
            'fields': ('views_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Admin interface for forum comments
    """
    list_display = ['post', 'author', 'content_preview', 'parent', 'is_edited', 'created_at']
    list_filter = ['is_edited', 'created_at']
    search_fields = ['content', 'author__email', 'post__title']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def content_preview(self, obj):
        """Show preview of comment content"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    """
    Admin interface for forum likes
    """
    list_display = ['post', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['post__title', 'user__email']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    Admin interface for content reports
    """
    list_display = ['post', 'reporter', 'reason', 'status', 'reviewed_by', 'created_at']
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['post__title', 'reporter__email', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Report Information', {
            'fields': ('post', 'reporter', 'reason', 'description')
        }),
        ('Review Status', {
            'fields': ('status', 'reviewed_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
