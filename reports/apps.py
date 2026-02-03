"""
Reports app configuration
"""

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = 'Reports and Analytics'
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import signals if any
        # import reports.signals
        pass