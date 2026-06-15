from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponse
from Documents.models import MemberDocument
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .permissions import IsAdminUser
from .serializers import (
    AdminMemberSerializer, SuspendMemberSerializer, 
    ReactivateMemberSerializer, AdminDocumentSerializer, 
    ApproveDocumentSerializer, RejectDocumentSerializer,
    AdminNoteSerializer, CreateAdminNoteSerializer,
    AssignApfNumberSerializer,
)
from .services import MemberManagementService, DocumentManagementService
from .models import MembershipStatus, DocumentStatus, AdminNote
import csv
from datetime import datetime


User = get_user_model()


class AdminMemberListView(APIView):
    """
    View to list all registered members with filtering capabilities
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        """Get queryset of members with optional filtering"""
        queryset = User.objects.filter(role='2')  # Only members, not admins
        
        # Apply status filter
        status_param = self.request.query_params.get('status', None)
        if status_param:
            if status_param.upper() == 'SUSPENDED':
                # Filter for users who are inactive or have an active suspension record
                queryset = queryset.filter(
                    Q(is_active=False) | 
                    Q(suspension_record__isnull=False, suspension_record__reactivated_at__isnull=True)
                )
            elif status_param.upper() == 'ACTIVE':
                # Filter for users who are active and don't have an active suspension
                queryset = queryset.filter(
                    is_active=True
                ).exclude(
                    suspension_record__isnull=False,
                    suspension_record__reactivated_at__isnull=True
                )
        
        # Apply search filter
        search_param = self.request.query_params.get('search', None)
        if search_param:
            queryset = queryset.filter(
                email__icontains=search_param
            ) | queryset.filter(
                first_name__icontains=search_param
            ) | queryset.filter(
                last_name__icontains=search_param
            )
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Get all registered members with optional filtering",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status (ACTIVE, SUSPENDED)", type=openapi.TYPE_STRING),
            openapi.Parameter('search', openapi.IN_QUERY, description="Search by name or email", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response('Success', AdminMemberSerializer(many=True)),
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required'
        }
    )
    def get(self, request):
        """
        Get all registered members with optional filtering
        Query params:
        - status: Filter by membership status (ACTIVE, SUSPENDED, PENDING)
        - search: Search by name or email
        """
        members = self.get_queryset()
        serializer = AdminMemberSerializer(members, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class AdminMemberExportCSVView(APIView):
    """
    View to export all members to CSV
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        """Get queryset of members with optional filtering"""
        queryset = User.objects.filter(role='2')  # Only members, not admins
        
        # Apply status filter
        status_param = self.request.query_params.get('status', None)
        if status_param:
            if status_param.upper() == 'SUSPENDED':
                queryset = queryset.filter(
                    Q(is_active=False) | 
                    Q(suspension_record__isnull=False, suspension_record__reactivated_at__isnull=True)
                )
            elif status_param.upper() == 'ACTIVE':
                queryset = queryset.filter(
                    is_active=True
                ).exclude(
                    suspension_record__isnull=False,
                    suspension_record__reactivated_at__isnull=True
                )
        
        # Apply search filter
        search_param = self.request.query_params.get('search', None)
        if search_param:
            queryset = queryset.filter(
                email__icontains=search_param
            ) | queryset.filter(
                first_name__icontains=search_param
            ) | queryset.filter(
                last_name__icontains=search_param
            )
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Export all members to CSV file with optional filtering",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status (ACTIVE, SUSPENDED)", type=openapi.TYPE_STRING),
            openapi.Parameter('search', openapi.IN_QUERY, description="Search by name or email", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response('CSV file download'),
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required'
        }
    )
    def get(self, request):
        """
        Export all members to CSV
        Query params:
        - status: Filter by membership status (ACTIVE, SUSPENDED)
        - search: Search by name or email
        """
        members = self.get_queryset()
        
        # Create the HttpResponse object with CSV header
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'apf_members_export_{timestamp}.csv'
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create CSV writer
        writer = csv.writer(response)
        
        # Write header row
        writer.writerow([
            'Member ID',
            'APF Membership Number',
            'Email',
            'First Name',
            'Last Name',
            'Phone Number',
            'National ID',
            'Job Title',
            'Organization',
            'ICPAU Registration Number',
            'Membership Category',
            'Practising Status',
            'Years of Experience',
            'City',
            'Country',
            'Subscription Due Date',
            'Account Status',
            'Date Joined',
            'Last Updated'
        ])
        
        # Write data rows
        for member in members:
            # Determine account status
            if not member.is_active:
                account_status = 'Suspended'
            elif member.subscription_due_date:
                from django.utils import timezone
                if member.subscription_due_date < timezone.now().date():
                    account_status = 'Expired'
                else:
                    account_status = 'Active'
            else:
                account_status = 'Active'
            
            writer.writerow([
                member.id,
                member.apf_membership_number or '',
                member.email,
                member.first_name or '',
                member.last_name or '',
                member.phone_number or '',
                member.national_id_number or '',
                member.job_title or '',
                member.organization or '',
                member.icpau_registration_number or '',
                member.membership_category or '',
                member.practising_status or '',
                member.years_of_experience or '',
                member.city or '',
                member.country or '',
                member.subscription_due_date.strftime('%Y-%m-%d') if member.subscription_due_date else '',
                account_status,
                member.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                member.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response


class AdminMemberSuspendView(APIView):
    """
    View to suspend a member
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Suspend a member by ID",
        request_body=SuspendMemberSerializer,
        responses={
            200: 'Member suspended successfully',
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Member not found'
        }
    )
    def patch(self, request, member_id):
        """
        Suspend a member by ID
        Expected payload: {"reason": "reason for suspension"}
        """
        serializer = SuspendMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = serializer.validated_data.get('reason')
        suspension_type = serializer.validated_data.get('suspension_type', 'non_payment')
        
        success, message, suspended_member = MemberManagementService.suspend_member(
            member_id, reason, request.user, suspension_type
        )
        
        if success:
            return Response(
                {'message': message, 'suspended_member': suspended_member.id if suspended_member else None},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminMemberReactivateView(APIView):
    """
    View to reactivate a suspended member
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Reactivate a suspended member by ID",
        responses={
            200: 'Member reactivated successfully',
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Member not found'
        }
    )
    def patch(self, request, member_id):
        """
        Reactivate a member by ID
        """
        success, message, _ = MemberManagementService.reactivate_member(
            member_id, request.user
        )
        
        if success:
            return Response(
                {'message': message},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminPendingDocumentsView(APIView):
    """
    View to get pending documents for review
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Get all pending documents uploaded by members for review",
        responses={
            200: openapi.Response('Success', AdminDocumentSerializer(many=True)),
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required'
        }
    )
    def get(self, request):
        """
        Get all pending documents uploaded by members
        """
        pending_docs = MemberDocument.objects.filter(status=DocumentStatus.PENDING).order_by('-uploaded_at')
        serializer = AdminDocumentSerializer(pending_docs, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class AdminApproveDocumentView(APIView):
    """
    View to approve a document
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Approve a member document by ID",
        request_body=ApproveDocumentSerializer,
        responses={
            200: 'Document approved successfully',
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Document not found'
        }
    )
    def patch(self, request, document_id):
        """
        Approve a document by ID
        """
        serializer = ApproveDocumentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message, processed_doc = DocumentManagementService.approve_document(
            document_id, request.user
        )
        
        if success:
            return Response(
                {'message': message, 'processed_document': processed_doc.id if processed_doc else None},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminRejectDocumentView(APIView):
    """
    View to reject a document
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Reject a member document by ID",
        request_body=RejectDocumentSerializer,
        responses={
            200: 'Document rejected successfully',
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Document not found'
        }
    )
    def patch(self, request, document_id):
        """
        Reject a document by ID
        Expected payload: {"reason": "reason for rejection"}
        """
        serializer = RejectDocumentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = serializer.validated_data.get('reason')
        
        success, message, processed_doc = DocumentManagementService.reject_document(
            document_id, reason, request.user
        )
        
        if success:
            return Response(
                {'message': message, 'processed_document': processed_doc.id if processed_doc else None},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )



# Membership Invoice Management Views

from rest_framework import viewsets
from rest_framework.decorators import action
from .models import MembershipInvoice
from .serializers import MembershipInvoiceSerializer
from .membership_renewal_service import MembershipRenewalService


class MembershipInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing membership invoices (admin only)
    """
    queryset = MembershipInvoice.objects.all().select_related('user')
    serializer_class = MembershipInvoiceSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        """Filter invoices based on user role"""
        user = self.request.user
        
        # Admin can see all invoices
        if user.role == '1':  # Admin
            queryset = MembershipInvoice.objects.all().select_related('user')
        else:
            # Members can only see their own invoices
            queryset = MembershipInvoice.objects.filter(user=user)
        
        # Apply filters
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__full_name__icontains=search)
            )
        
        return queryset.order_by('-invoice_date', '-created_at')
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend invoice email"""
        invoice = self.get_object()
        
        # Check if user is admin
        if request.user.role != '1':
            return Response(
                {'error': 'Only admins can resend invoices'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Resend email
        success, message = MembershipRenewalService.send_renewal_invoice_email(
            invoice.user,
            invoice=invoice
        )
        
        if success:
            return Response({'message': message})
        else:
            return Response(
                {'error': message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get invoice statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'partial': queryset.filter(status='partial').count(),
            'paid': queryset.filter(status='paid').count(),
            'overdue': queryset.filter(status='overdue').count(),
            'cancelled': queryset.filter(status='cancelled').count(),
            'total_amount': sum(inv.total_amount for inv in queryset),
            'total_paid': sum(inv.amount_paid for inv in queryset),
            'total_outstanding': sum(inv.balance_due for inv in queryset),
        }
        
        return Response(stats)



class AdminNoteListCreateView(APIView):
    """
    View to list and create admin notes for a specific member
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Get all admin notes for a specific member",
        responses={
            200: openapi.Response('Success', AdminNoteSerializer(many=True)),
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Member not found'
        }
    )
    def get(self, request, member_id):
        """
        Get all admin notes for a specific member
        """
        try:
            member = User.objects.get(id=member_id, role='2')
        except User.DoesNotExist:
            return Response(
                {'error': 'Member not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        notes = AdminNote.objects.filter(member=member).select_related('admin', 'member')
        serializer = AdminNoteSerializer(notes, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Create a new admin note for a specific member",
        request_body=CreateAdminNoteSerializer,
        responses={
            201: openapi.Response('Note created successfully', AdminNoteSerializer),
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Member not found'
        }
    )
    def post(self, request, member_id):
        """
        Create a new admin note for a specific member
        Expected payload: {"note_text": "note content"}
        """
        try:
            member = User.objects.get(id=member_id, role='2')
        except User.DoesNotExist:
            return Response(
                {'error': 'Member not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CreateAdminNoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the note
        note = AdminNote.objects.create(
            member=member,
            admin=request.user,
            note_text=serializer.validated_data['note_text']
        )
        
        response_serializer = AdminNoteSerializer(note)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )


class AdminNoteDetailView(APIView):
    """
    View to retrieve, update, or delete a specific admin note
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, note_id):
        """Helper method to get note object"""
        try:
            return AdminNote.objects.select_related('admin', 'member').get(id=note_id)
        except AdminNote.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Get a specific admin note by ID",
        responses={
            200: openapi.Response('Success', AdminNoteSerializer),
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Note not found'
        }
    )
    def get(self, request, note_id):
        """
        Get a specific admin note by ID
        """
        note = self.get_object(note_id)
        if not note:
            return Response(
                {'error': 'Note not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AdminNoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Update a specific admin note by ID",
        request_body=CreateAdminNoteSerializer,
        responses={
            200: openapi.Response('Note updated successfully', AdminNoteSerializer),
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Note not found'
        }
    )
    def patch(self, request, note_id):
        """
        Update a specific admin note by ID
        Expected payload: {"note_text": "updated note content"}
        """
        note = self.get_object(note_id)
        if not note:
            return Response(
                {'error': 'Note not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CreateAdminNoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the note
        note.note_text = serializer.validated_data['note_text']
        note.save()
        
        response_serializer = AdminNoteSerializer(note)
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK
        )
    
    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Delete a specific admin note by ID",
        responses={
            204: 'Note deleted successfully',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Note not found'
        }
    )
    def delete(self, request, note_id):
        """
        Delete a specific admin note by ID
        """
        note = self.get_object(note_id)
        if not note:
            return Response(
                {'error': 'Note not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        note.delete()
        return Response(
            {'message': 'Note deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


class AdminDeleteMemberView(APIView):
    """
    Permanently delete a member and ALL their associated data.
    Also removes/rejects their linked applications so the email
    is freed for re-registration.
    Admins (role=1) are protected and cannot be deleted via this endpoint.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description=(
            "Permanently delete a member and all their data. "
            "Their application is also rejected so the email can be reused for re-registration. "
            "Admins cannot be deleted."
        ),
        responses={
            200: 'Member deleted successfully',
            400: 'Cannot delete admin accounts',
            403: 'Forbidden',
            404: 'Member not found',
        }
    )
    def delete(self, request, member_id):
        import logging
        logger = logging.getLogger(__name__)

        try:
            member = User.objects.get(id=member_id)
        except User.DoesNotExist:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)

        if member.role == '1':
            return Response(
                {'error': 'Admin accounts cannot be deleted via this endpoint.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = member.email

        # Reject all non-rejected applications for this email so the
        # email is freed for re-registration (constraint is NOT rejected)
        try:
            from applications.models import Application
            freed = Application.objects.filter(
                email__iexact=email
            ).exclude(status='rejected').update(status='rejected')
            if freed:
                logger.info(
                    f"Freed {freed} application(s) for {email} by marking as rejected"
                )
        except Exception as e:
            logger.warning(f"Could not free applications for {email}: {e}")

        logger.warning(
            f"Admin {request.user.email} permanently deleted member {email} (id={member_id})"
        )
        member.delete()

        return Response(
            {'message': f'Member {email} deleted. Their email is now available for re-registration.'},
            status=status.HTTP_200_OK
        )


class AdminDeleteApplicationView(APIView):
    """
    Permanently delete an application and its linked user/payments/documents.
    Marks the application as rejected first (freeing the email for re-registration),
    then deletes the linked user account if present.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description=(
            "Permanently delete an application. "
            "The email is freed for re-registration. "
            "If a member account is linked, it is also deleted."
        ),
        responses={
            200: 'Application deleted successfully',
            403: 'Forbidden',
            404: 'Application not found',
        }
    )
    def delete(self, request, application_id):
        from applications.models import Application
        import logging
        logger = logging.getLogger(__name__)

        try:
            application = Application.objects.select_related('user').get(id=application_id)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        app_id_str = application.application_id
        email = application.email
        deleted_user_email = None

        # Mark as rejected BEFORE deleting so the unique constraint is released,
        # freeing the email for re-registration even if we only delete the user.
        application.status = 'rejected'
        application.save(update_fields=['status'])

        # If there's a linked user (and they're not an admin), delete them
        linked_user = application.user
        if linked_user and linked_user.role != '1':
            deleted_user_email = linked_user.email
            logger.warning(
                f"Admin {request.user.email} deleting application {app_id_str} "
                f"and linked member {deleted_user_email}"
            )
            # Also reject any other applications for this email
            Application.objects.filter(
                email__iexact=email
            ).exclude(status='rejected').update(status='rejected')
            linked_user.delete()  # cascades to payments, docs, notifications etc.
        else:
            logger.warning(
                f"Admin {request.user.email} deleting application {app_id_str} "
                f"(email={email}, no linked user)"
            )
            application.delete()

        msg = f'Application {app_id_str} deleted. Email {email} is now available for re-registration.'
        if deleted_user_email:
            msg += f' Linked member account ({deleted_user_email}) and all associated data also deleted.'

        return Response({'message': msg}, status=status.HTTP_200_OK)


class AdminDeletePaymentView(APIView):
    """
    Permanently delete a single manual payment record.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Permanently delete a manual payment record.",
        responses={
            200: 'Payment deleted successfully',
            403: 'Forbidden',
            404: 'Payment not found',
        }
    )
    def delete(self, request, payment_id):
        from payments.models import ManualPayment
        import logging
        logger = logging.getLogger(__name__)

        try:
            payment = ManualPayment.objects.select_related('user', 'application').get(id=payment_id)
        except ManualPayment.DoesNotExist:
            return Response({'error': 'Payment record not found'}, status=status.HTTP_404_NOT_FOUND)

        ref = payment.reference or str(payment_id)
        member_email = payment.user.email if payment.user else 'unknown'
        logger.warning(
            f"Admin {request.user.email} deleted ManualPayment {payment_id} "
            f"(ref={ref}, member={member_email})"
        )
        payment.delete()

        return Response(
            {'message': f'Payment record {ref} deleted successfully.'},
            status=status.HTTP_200_OK
        )


class AdminAssignApfNumberView(APIView):
    """
    Admin endpoint to assign or update an APF membership number for a member.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Assign or update the APF membership number for a member (format: APF/M/***)",
        request_body=AssignApfNumberSerializer,
        responses={
            200: openapi.Response('APF number assigned successfully'),
            400: 'Invalid format or number already in use',
            401: 'Unauthorized',
            403: 'Forbidden - Admin access required',
            404: 'Member not found',
        }
    )
    def patch(self, request, member_id):
        try:
            member = User.objects.get(id=member_id, role='2')
        except User.DoesNotExist:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssignApfNumberSerializer(
            data=request.data,
            context={'member_id': member_id}
        )
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        apf_number = serializer.validated_data['apf_membership_number']
        member.apf_membership_number = apf_number
        member.save(update_fields=['apf_membership_number'])

        import logging
        logging.getLogger(__name__).info(
            f"Admin {request.user.email} assigned APF number {apf_number} to member {member.email}"
        )

        return Response({
            'message': f'APF membership number {apf_number} assigned to {member.email}.',
            'apf_membership_number': apf_number,
            'member_id': member.id,
        }, status=status.HTTP_200_OK)


class BulkMemberRegistrationView(APIView):
    """
    Admin endpoint to register multiple members at once.
    Accepts a list of members with name, email, and phone number.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        tags=["admin-management"],
        operation_description="Bulk register multiple members. Returns created members with temporary passwords.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['members'],
            properties={
                'members': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        required=['first_name', 'last_name', 'email'],
                        properties={
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, format='email'),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            }
        ),
        responses={
            201: openapi.Response('Members registered successfully'),
            400: 'Validation error',
            403: 'Forbidden - Admin access required',
        }
    )
    def post(self, request):
        from .serializers import BulkMemberRegistrationSerializer
        from .services import BulkRegistrationService
        import logging
        logger = logging.getLogger(__name__)

        serializer = BulkMemberRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"BulkRegister validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = BulkRegistrationService.register_members(
            members_data=serializer.validated_data['members'],
            registered_by=request.user,
        )

        return Response({
            'message': f"{len(result['created'])} member(s) registered successfully.",
            'created': result['created'],
            'failed': result['failed'],
        }, status=status.HTTP_201_CREATED)


class AdminResetMemberPasswordView(APIView):
    """
    Admin endpoint to regenerate a temporary password for a member
    and resend the welcome email with the new credentials.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, member_id):
        try:
            member = User.objects.get(id=member_id, role='2')
        except User.DoesNotExist:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)

        from .services import BulkRegistrationService
        from authentication.email_service_smtp import EmailService
        import logging
        logger = logging.getLogger(__name__)

        temp_password = BulkRegistrationService.generate_temp_password()
        member.set_password(temp_password)
        member.must_change_password = True
        member.email_verified = False
        member.save(update_fields=['password', 'must_change_password', 'email_verified'])

        email_sent = EmailService.send_temp_credentials_email(
            email=member.email,
            first_name=member.first_name or member.email.split('@')[0],
            temp_password=temp_password,
        )

        logger.info(f"Admin {request.user.email} reset password for member {member.email}")

        return Response({
            'email': member.email,
            'full_name': member.full_name,
            'temp_password': temp_password,
            'email_sent': email_sent,
        }, status=status.HTTP_200_OK)
