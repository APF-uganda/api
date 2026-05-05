# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
# Import is optional - only loads if Celery is installed
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed - that's okay, you can use cron instead
    pass
