"""
Email notification service for forum activities
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.html import strip_tags
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def get_active_members_emails(exclude_user=None):
    """Get all active member emails who have notifications enabled, optionally excluding a specific user"""
    users = User.objects.filter(
        is_active=True, 
        role='2',  # role='2' is member
        email_notifications_enabled=True
    )
    if exclude_user:
        users = users.exclude(id=exclude_user.id)
    return list(users.values_list('email', flat=True))


def send_new_post_notification(post):
    """
    Send email notification to all members when a new forum post is created
    """
    try:
        # Get all member emails except the post author who have new post notifications enabled
        recipient_emails = list(User.objects.filter(
            is_active=True,
            role='2',
            email_notifications_enabled=True,
            email_new_posts=True
        ).exclude(id=post.author.id).values_list('email', flat=True))
        
        if not recipient_emails:
            logger.info("No recipients found for new post notification")
            return
        
        # Prepare email context
        context = {
            'post_title': post.title,
            'post_content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
            'author_name': post.author.full_name or post.author.email,
            'category': post.category.name if post.category else 'General',
            'post_url': f"{settings.FRONTEND_URL}/forum/posts/{post.id}",
            'forum_url': f"{settings.FRONTEND_URL}/forum",
        }
        
        # Render HTML email
        html_content = render_to_string('email/forum_new_post.html', context)
        text_content = strip_tags(html_content)
        
        subject = f"New Forum Post: {post.title}"
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            bcc=recipient_emails  # Use BCC to hide recipients from each other
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"New post notification sent to {len(recipient_emails)} members")
        
    except Exception as e:
        logger.error(f"Error sending new post notification: {str(e)}")


def send_new_comment_notification(comment):
    """
    Send email notification when someone comments on a post
    """
    try:
        post = comment.post
        
        # Notify post author (if they're not the commenter and have notifications enabled)
        recipients = []
        if (post.author != comment.author and post.author.is_active and 
            post.author.email_notifications_enabled and post.author.email_new_comments):
            recipients.append(post.author.email)
        
        # Notify other commenters on the same post (excluding current commenter) who have notifications enabled
        other_commenters = User.objects.filter(
            forum_comments__post=post,
            is_active=True,
            email_notifications_enabled=True,
            email_new_comments=True
        ).exclude(id=comment.author.id).distinct()
        
        recipients.extend(other_commenters.values_list('email', flat=True))
        
        # Remove duplicates
        recipients = list(set(recipients))
        
        if not recipients:
            logger.info("No recipients found for comment notification")
            return
        
        # Prepare email context
        context = {
            'post_title': post.title,
            'comment_content': comment.content[:200] + '...' if len(comment.content) > 200 else comment.content,
            'commenter_name': comment.author.full_name or comment.author.email,
            'post_url': f"{settings.FRONTEND_URL}/forum/posts/{post.id}",
            'is_reply': comment.parent is not None,
        }
        
        # Render HTML email
        html_content = render_to_string('email/forum_new_comment.html', context)
        text_content = strip_tags(html_content)
        
        subject = f"New Comment on: {post.title}"
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            bcc=recipients
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Comment notification sent to {len(recipients)} users")
        
    except Exception as e:
        logger.error(f"Error sending comment notification: {str(e)}")


def send_post_reply_notification(comment):
    """
    Send email notification to post author when someone replies to their post
    """
    try:
        post = comment.post
        
        # Only notify if the commenter is not the post author and author has notifications enabled
        if (post.author == comment.author or not post.author.is_active or
            not post.author.email_notifications_enabled or not post.author.email_post_replies):
            return
        
        # Prepare email context
        context = {
            'post_title': post.title,
            'comment_content': comment.content[:200] + '...' if len(comment.content) > 200 else comment.content,
            'commenter_name': comment.author.full_name or comment.author.email,
            'post_url': f"{settings.FRONTEND_URL}/forum/posts/{post.id}",
        }
        
        # Render HTML email
        html_content = render_to_string('email/forum_post_reply.html', context)
        text_content = strip_tags(html_content)
        
        subject = f"New Reply on Your Post: {post.title}"
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[post.author.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Reply notification sent to post author: {post.author.email}")
        
    except Exception as e:
        logger.error(f"Error sending reply notification: {str(e)}")


def send_discussion_digest(frequency='daily'):
    """
    Send a digest email of forum activity
    frequency: 'daily' or 'weekly'
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import ForumPost, Comment
        
        # Calculate time range
        if frequency == 'daily':
            time_threshold = timezone.now() - timedelta(days=1)
        else:  # weekly
            time_threshold = timezone.now() - timedelta(days=7)
        
        # Get recent posts and comments
        recent_posts = ForumPost.objects.filter(
            created_at__gte=time_threshold,
            status='published'
        ).select_related('author', 'category')[:10]
        
        recent_comments = Comment.objects.filter(
            created_at__gte=time_threshold
        ).select_related('author', 'post')[:10]
        
        if not recent_posts and not recent_comments:
            logger.info(f"No activity for {frequency} digest")
            return
        
        # Get all member emails
        recipient_emails = get_active_members_emails()
        
        if not recipient_emails:
            logger.info("No recipients found for digest")
            return
        
        # Prepare email context
        context = {
            'frequency': frequency,
            'recent_posts': recent_posts,
            'recent_comments': recent_comments,
            'forum_url': f"{settings.FRONTEND_URL}/forum",
            'post_count': recent_posts.count(),
            'comment_count': recent_comments.count(),
        }
        
        # Render HTML email
        html_content = render_to_string('email/forum_digest.html', context)
        text_content = strip_tags(html_content)
        
        subject = f"APF Forum {frequency.capitalize()} Digest"
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            bcc=recipient_emails
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"{frequency.capitalize()} digest sent to {len(recipient_emails)} members")
        
    except Exception as e:
        logger.error(f"Error sending {frequency} digest: {str(e)}")
