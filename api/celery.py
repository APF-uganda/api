"""
Celery configuration for APF Portal.

This module configures Celery for background task processing and scheduled tasks.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

app = Celery('api')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule - Scheduled Tasks
app.conf.beat_schedule = {
    # News fetch - runs twice a week (Monday and Thursday at 9:00 AM)
    'fetch-icpau-news-monday-thursday': {
        'task': 'news.tasks.fetch_icpau_news',
        'schedule': crontab(hour=9, minute=0, day_of_week='1,4'),  # Monday=1, Thursday=4
    },
    
    # Payment polling - every 10 seconds
    'poll-pending-payments': {
        'task': 'payments.tasks.poll_pending_payments',
        'schedule': 10.0,  # Every 10 seconds
    },
    
    # Check timeout payments - every 5 minutes
    'check-timeout-payments': {
        'task': 'payments.tasks.check_timeout_payments',
        'schedule': crontab(minute='*/5'),
    },
    
    # Cleanup old webhook notifications - daily at 2:00 AM
    'cleanup-webhook-notifications': {
        'task': 'payments.tasks.cleanup_old_webhook_notifications',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {'days': 30}
    },
    
    # Generate webhook stats - every hour
    'generate-webhook-stats': {
        'task': 'payments.tasks.generate_webhook_stats',
        'schedule': crontab(minute=0),
    },
}

# Celery Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Kampala',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
