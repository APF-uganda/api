from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Application
from Documents.models import Document
from notifications.services import create_notification
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature


from django.core.cache import cache

import random
import uuid
import logging
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from authentication.models import OTP 
User = get_user_model()


def create_application_documents(application, uploaded_files, document_types=None):
    """Attach uploaded documents to an existing application."""
    import logging
    logger = logging.getLogger(__name__)
    
    document_types = document_types or []
    created_documents = []
    
    logger.info(f"Creating documents for application {application.id}")
    logger.info(f"Number of files to upload: {len(uploaded_files)}")
    logger.info(f"Document types: {document_types}")
    
    for index, uploaded_file in enumerate(uploaded_files):
        document_type = document_types[index] if index < len(document_types) else ''
        
        logger.info(f"Processing file {index + 1}/{len(uploaded_files)}: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        try:
            # Create the document - Django will handle saving the file and may rename it
            document = Document.objects.create(
                application=application,
                file=uploaded_file,  # Django saves this and may rename it
                file_name=uploaded_file.name,  # Original filename for display
                file_size=uploaded_file.size,
                file_type=uploaded_file.content_type,
                document_type=document_type
            )
            
            # Log the actual saved file path for debugging
            logger.info(f"✓ Document created: ID={document.id}, Original name={uploaded_file.name}, Saved as={document.file.name}")
            
            # Verify the file was actually saved to disk
            import os
            from django.conf import settings
            file_path = os.path.join(settings.MEDIA_ROOT, document.file.name)
            if os.path.exists(file_path):
                logger.info(f"✓ File verified on disk: {file_path}")
            else:
                logger.error(f"✗ FILE NOT FOUND ON DISK: {file_path}")
            
            created_documents.append(document)
            
        except Exception as e:
            logger.error(f"✗ Failed to create document for file {uploaded_file.name}: {str(e)}", exc_info=True)
            # Continue with other files even if one fails
            continue
    
    logger.info(f"Successfully created {len(created_documents)} out of {len(uploaded_files)} documents")
    return created_documents


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
import random
import logging


logger = logging.getLogger(__name__)



logger = logging.getLogger(__name__)

import uuid
import random
import logging
from django.utils import timezone
from datetime import timedelta

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

from django.core.signing import TimestampSigner, SignatureExpired, BadSignature

# This is our "Virtual Database" - it uses your SECRET_KEY to verify the code
signer = TimestampSigner()

def send_registration_otp(email, username):
    #Generate 6-digit code
    otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    
   
    signed_token = signer.sign(f"{email}:{otp_code}")
    
    
    try:
        context = {'user_name': username, 'verification_code': otp_code}
        html_content = render_to_string('registration/email_otp.html', context)
        
        msg = EmailMultiAlternatives(
            subject=f"{otp_code} is your verification code",
            body=strip_tags(html_content),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        # We return the token so the ViewSet can send it to React
        return signed_token 
    except Exception as e:
        logger.error(f"Mail failed: {str(e)}")
        raise e

def verify_registration_otp(email, code, signed_token):
    """
    Checks the code against the signed token. No database call required!
    """
    try:
        # Check if the token is valid and less than 15 minutes (900s) old
        original_value = signer.unsign(signed_token, max_age=900)
        
        # Verify the email and code match the stamp
        if original_value == f"{email}:{code}":
            return True
    except (SignatureExpired, BadSignature):
        # Token was tampered with or expired
        return False
    return False

    