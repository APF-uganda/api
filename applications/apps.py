from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications'
    verbose_name = 'Membership Applications'
    
    def ready(self):
        """Import signals when app is ready"""
        import applications.signals
