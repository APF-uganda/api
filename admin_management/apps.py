from django.apps import AppConfig


class AdminManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_management"

    def ready(self):
        # Only start the scheduler when running the actual web server.
        # Skip during migrations, shell, management commands, tests, etc.
        import sys
        args = sys.argv
        if len(args) < 2:
            return
        # Only start for runserver (dev) or gunicorn/uvicorn (production)
        # gunicorn/uvicorn don't use manage.py so sys.argv[0] won't be manage.py
        is_runserver = args[1] == "runserver"
        is_wsgi_server = "gunicorn" in args[0] or "uvicorn" in args[0]
        running_tests = "test" in args

        if running_tests:
            return
        if not (is_runserver or is_wsgi_server):
            return

        from admin_management.scheduler import start
        start()
