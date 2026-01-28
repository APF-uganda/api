from django.shortcuts import get_object_or_404
from .models import Application, Document
from notifications.services import create_notification


def create_application(validated_data, uploaded_files):
    """Create application and attach uploaded documents."""
    application = Application.objects.create(**validated_data)
    for uploaded_file in uploaded_files:
        Document.objects.create(
            application=application,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_type=uploaded_file.content_type
        )
    return application


def approve_application(application_id):
    """Approve an application and notify the user."""
    app = get_object_or_404(Application, pk=application_id)
    app.status = "approved"
    app.save()

    if app.user:
        create_notification(
            application=app,
            user=app.user,
            message="Your membership application has been approved.",
            type="success"
        )
    return app


def reject_application(application_id):
    """Reject an application and notify the user."""
    app = get_object_or_404(Application, pk=application_id)
    app.status = "rejected"
    app.save()

    if app.user:
        create_notification(
            application=app,
            user=app.user,
            message="Your membership application has been rejected.",
            type="error"
        )
    return app


def retry_application(application_id):
    """Reset an application back to pending (no notification)."""
    app = get_object_or_404(Application, pk=application_id)
    app.status = "pending"
    app.save()
    return app