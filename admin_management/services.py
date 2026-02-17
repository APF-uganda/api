from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from Documents.models import MemberDocument
from notifications.models import UserNotification
from .models import SuspendedMember, ProcessedDocument, MembershipStatus, DocumentStatus


User = get_user_model()


class MemberManagementService:
    """
    Service class for managing member-related operations
    """
    
    @staticmethod
    @transaction.atomic
    def suspend_member(member_id, reason, admin_user):
        """
        Suspend a member for non-payment of annual subscription
        
        Args:
            member_id (int): ID of the member to suspend
            reason (str): Reason for suspension
            admin_user: Admin user performing the action
            
        Returns:
            tuple: (success: bool, message: str, suspended_member: SuspendedMember or None)
        """
        try:
            member = User.objects.get(id=member_id, role='2')  # Ensure it's a member, not admin
            
            # Set user as inactive
            member.is_active = False
            member.save(update_fields=['is_active'])
            
            # Create/update suspension record
            suspended_member, created = SuspendedMember.objects.update_or_create(
                user=member,
                defaults={
                    'suspension_reason': reason,
                    'reactivated_at': None,  # Clear any previous reactivation
                }
            )
            
            # Send notification to member
            UserNotification.objects.create(
                user=member,
                title="Account Suspended",
                message=f"Your account has been suspended. Reason: {reason}. Please pay your annual subscription fee to reactivate your account.",
                notification_type='system',
                priority='high'
            )
            
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