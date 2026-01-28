from .models import Notification

def create_notification(application, user, message, type="info"):
    """
    Create a notification for a given application and user.
    """
    return Notification.objects.create(
        application=application,
        user=user,
        message=message,
        type=type
    )