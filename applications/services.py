from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Application, Document
from notifications.services import create_notification

User = get_user_model()


def create_application_documents(application, uploaded_files, document_types=None):
    """Attach uploaded documents to an existing application."""
    document_types = document_types or []
    for index, uploaded_file in enumerate(uploaded_files):
        document_type = document_types[index] if index < len(document_types) else ''
        Document.objects.create(
            application=application,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_type=uploaded_file.content_type,
            document_type=document_type
        )


def approve_application(application_id):
    """Approve an application and notify the user."""
    app = get_object_or_404(Application, pk=application_id)
    app.status = "approved"
    app.save()

    if app.user:
        if not app.user.is_active:
            app.user.is_active = True
            app.user.save(update_fields=['is_active'])
        
        # Create notification
        create_notification(
            application=app,
            user=app.user,
            message="Your membership application has been approved.",
            type="success"
        )
        
        # Send welcome announcement
        try:
            from AdminNotifications.services import send_welcome_announcement
            send_welcome_announcement(app.user)
        except Exception as e:
            print(f"Error sending welcome announcement: {e}")
    
    return app


def reject_application(application_id):
    """Reject an application and notify the user."""
    app = get_object_or_404(Application, pk=application_id)
    app.status = "rejected"
    app.save()

    user = app.user
    if not user and app.email:
        user = User.objects.filter(email__iexact=app.email).first()

    if user:
        has_non_rejected = Application.objects.filter(
            email__iexact=user.email
        ).exclude(status='rejected').exists()

        if not has_non_rejected and user.is_active:
            user.is_active = False
            user.save(update_fields=['is_active'])

        create_notification(
            application=app,
            user=user,
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
