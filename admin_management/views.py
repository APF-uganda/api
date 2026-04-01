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
    AdminNoteSerializer, CreateAdminNoteSerializer
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
        
        success, message, suspended_member = MemberManagementService.suspend_member(
            member_id, reason, request.user
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
