"""
Payments app configuration.
"""
from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = 'Mobile Money Payments'
    
    def ready(self):
        """Import signals when app is ready"""
        import payments.signals
