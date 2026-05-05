"""
Celery tasks for news fetching.

Background tasks for fetching ICPAU news from RSS feed.
"""
import logging
from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='news.tasks.fetch_icpau_news')
def fetch_icpau_news(self):
    """
    Celery task to fetch ICPAU news from RSS feed.
    
    This task runs the newsfetch management command.
    Scheduled to run twice a week (Monday and Thursday at 9:00 AM).
    """
    try:
        logger.info("Starting ICPAU news fetch task")
        call_command('newsfetch')
        logger.info("ICPAU news fetch task completed successfully")
        return {'status': 'success', 'message': 'News fetched successfully'}
    except Exception as e:
        logger.error(f"ICPAU news fetch task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=300, max_retries=3)  # Retry after 5 minutes, max 3 times
