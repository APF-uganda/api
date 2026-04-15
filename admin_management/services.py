import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from Documents.models import MemberDocument
from notifications.models import UserNotification
from .models import SuspendedMember, ProcessedDocument, MembershipStatus, DocumentStatus
from payments.models import ManualPayment

logger = logging.getLogger(__name__)
User = get_user_model()


def _extract_manual_payment_id(document):
    doc_type = (getattr(document, 'document_type', '') or '').upper()
    prefix = 'PAYMENT_RECEIPT_'
    if not doc_type.startswith(prefix):
        return None
    suffix = doc_type[len(prefix):]
    return int(suffix) if suffix.isdigit() else None


class MemberManagementService:
    """
    Service class for managing member-related operations
    """
    
    @staticmethod
    @transaction.atomic
    def suspend_member(member_id, reason, admin_user, suspension_type='non_payment'):
        """
        Suspend a member.
        suspension_type: 'non_payment' or 'policy_violation'
        """
        try:
            member = User.objects.get(id=member_id, role='2')
            
            member.is_active = False
            member.save(update_fields=['is_active'])
            
            suspended_member, created = SuspendedMember.objects.update_or_create(
                user=member,
                defaults={
                    'suspension_reason': reason,
                    'suspension_type': suspension_type,
                    'reactivated_at': None,
                }
            )
            
            # In-app notification
            UserNotification.objects.create(
                user=member,
                title="Account Suspended",
                message=f"Your account has been suspended. Reason: {reason}.",
                notification_type='system',
                priority='high'
            )

            # Email — different template per type
            try:
                from authentication.email_service_smtp import EmailService
                from django.conf import settings
                frontend_url = getattr(settings, 'FRONTEND_URL', 'https://apfuganda.org').rstrip('/')
                renewal_url = f"{frontend_url}/payments"
                user_name = member.first_name or member.email.split('@')[0]
                suspended_at = timezone.now().strftime('%d %B %Y')

                if suspension_type == 'non_payment':
                    EmailService.send_non_payment_suspension_email(
                        email=member.email,
                        user_name=user_name,
                        reason=reason,
                        suspended_at=suspended_at,
                        renewal_url=renewal_url,
                    )
                else:
                    EmailService.send_suspension_email(
                        email=member.email,
                        user_name=user_name,
                        reason=reason,
                        suspended_at=suspended_at,
                        renewal_url=renewal_url,
                    )
            except Exception as e:
                logger.warning(f"Failed to send suspension email to {member.email}: {e}")
            
            return True, "Member suspended successfully", suspended_member
            
        except User.DoesNotExist:
            return False, "Member not found", None
        except Exception as e:
            return False, f"Error suspending member: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def reactivate_member(member_id, admin_user):
        """
        Reactivate a suspended member
        
        Args:
            member_id (int): ID of the member to reactivate
            admin_user: Admin user performing the action
            
        Returns:
            tuple: (success: bool, message: str, suspended_member: SuspendedMember or None)
        """
        try:
            member = User.objects.get(id=member_id, role='2')  # Ensure it's a member, not admin
            
            # Set user as active
            member.is_active = True
            member.save(update_fields=['is_active'])
            
            # Update suspension record
            try:
                suspended_record = member.suspension_record
                suspended_record.reactivated_at = timezone.now()
                suspended_record.save(update_fields=['reactivated_at'])
            except SuspendedMember.DoesNotExist:
                pass  # Member was not suspended
            
            # Send notification to member
            UserNotification.objects.create(
                user=member,
                title="Account Reactivated",
                message="Your account has been reactivated successfully. Welcome back!",
                notification_type='system',
                priority='medium'
            )
            
            return True, "Member reactivated successfully", None
            
        except User.DoesNotExist:
            return False, "Member not found", None
        except Exception as e:
            return False, f"Error reactivating member: {str(e)}", None


class DocumentManagementService:
    """
    Service class for managing document-related operations
    """
    
    @staticmethod
    @transaction.atomic
    def approve_document(document_id, admin_user):
        """
        Approve a document uploaded by a member
        
        Args:
            document_id (int): ID of the document to approve
            admin_user: Admin user performing the action
            
        Returns:
            tuple: (success: bool, message: str, processed_document: ProcessedDocument or None)
        """
        try:
            document = MemberDocument.objects.get(id=document_id)
            
            # Update document status
            document.status = DocumentStatus.APPROVED
            document.save(update_fields=['status'])

            # If this is a renewal receipt document, verify linked manual payment.
            payment_id = _extract_manual_payment_id(document)
            if payment_id:
                payment = ManualPayment.objects.filter(id=payment_id).first()
                if payment and payment.status != ManualPayment.STATUS_VERIFIED:
                    payment.verify(admin_user, notes='Receipt approved via admin document review')
            
            # Create/update processed record
            processed_doc, created = ProcessedDocument.objects.update_or_create(
                document=document,
                defaults={
                    'status': DocumentStatus.APPROVED,
                    'approved_at': timezone.now(),
                    'approved_by': admin_user,
                }
            )
            
            # Send notification to member
            UserNotification.objects.create(
                user=document.user,
                title="Document Approved",
                message=f"Your uploaded document '{document.file_name}' has been approved.",
                notification_type='system',
                priority='medium'
            )
            
            return True, "Document approved successfully", processed_doc
            
        except MemberDocument.DoesNotExist:
            return False, "Document not found", None
        except Exception as e:
            return False, f"Error approving document: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def reject_document(document_id, reason, admin_user):
        """
        Reject a document uploaded by a member
        
        Args:
            document_id (int): ID of the document to reject
            reason (str): Reason for rejection
            admin_user: Admin user performing the action
            
        Returns:
            tuple: (success: bool, message: str, processed_document: ProcessedDocument or None)
        """
        try:
            document = MemberDocument.objects.get(id=document_id)
            
            # Update document status
            document.status = DocumentStatus.REJECTED
            document.admin_feedback = reason
            document.save(update_fields=['status', 'admin_feedback'])

            # If this is a renewal receipt document, reject linked manual payment.
            payment_id = _extract_manual_payment_id(document)
            if payment_id:
                payment = ManualPayment.objects.filter(id=payment_id).first()
                if payment and payment.status != ManualPayment.STATUS_REJECTED:
                    payment.reject(admin_user, notes=reason or 'Receipt rejected via admin document review')
            
            # Create/update processed record
            processed_doc, created = ProcessedDocument.objects.update_or_create(
                document=document,
                defaults={
                    'status': DocumentStatus.REJECTED,
                    'rejection_reason': reason,
                    'rejected_at': timezone.now(),
                }
            )
            
            # Send notification to member
            UserNotification.objects.create(
                user=document.user,
                title="Document Rejected",
                message=f"Your uploaded document '{document.file_name}' has been rejected. Reason: {reason}",
                notification_type='system',
                priority='high'
            )
            
            return True, "Document rejected successfully", processed_doc
            
        except MemberDocument.DoesNotExist:
            return False, "Document not found", None
        except Exception as e:
            return False, f"Error rejecting document: {str(e)}", None


class BulkRegistrationService:
    """Service for bulk member registration by admin"""

    @staticmethod
    def generate_temp_password():
        """Generate a secure temporary password"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        # Ensure at least one of each required type
        password = (
            secrets.choice(string.ascii_uppercase) +
            secrets.choice(string.ascii_lowercase) +
            secrets.choice(string.digits) +
            secrets.choice("!@#$%") +
            ''.join(secrets.choice(alphabet) for _ in range(6))
        )
        # Shuffle to avoid predictable pattern
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        return ''.join(password_list)

    @staticmethod
    def register_members(members_data, registered_by):
        """
        Bulk register members and return results.

        Args:
            members_data: list of dicts with first_name, last_name, email, phone_number
            registered_by: admin User performing the action

        Returns:
            dict with 'created', 'failed' lists
        """
        from authentication.models import UserRole
        from authentication.email_service_smtp import EmailService

        created = []
        failed = []

        for entry in members_data:
            email = entry['email'].lower()
            try:
                if User.objects.filter(email=email).exists():
                    failed.append({'email': email, 'reason': 'A user with this email already exists.'})
                    continue

                temp_password = BulkRegistrationService.generate_temp_password()

                with transaction.atomic():
                    user = User.objects.create_user(
                        email=email,
                        password=temp_password,
                        first_name=entry['first_name'],
                        last_name=entry['last_name'],
                        phone_number=entry.get('phone_number', ''),
                        icpau_registration_number=entry.get('icpau_registration_number', ''),
                        role=UserRole.MEMBER,
                        is_active=True,
                        must_change_password=True,
                        email_verified=False,
                    )

                # Send email outside the transaction so a send failure doesn't roll back the user
                email_sent = EmailService.send_temp_credentials_email(
                    email=email,
                    first_name=entry['first_name'],
                    temp_password=temp_password,
                )

                created.append({
                    'id': user.id,
                    'email': user.email,
                    'full_name': f"{user.first_name} {user.last_name}",
                    'temp_password': temp_password,
                    'email_sent': email_sent,
                })
            except Exception as e:
                failed.append({
                    'email': email,
                    'reason': str(e),
                })

        return {'created': created, 'failed': failed}
