from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Q
from Documents.models import MemberDocument
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .permissions import IsAdminUser
from .serializers import (
    AdminMemberSerializer, SuspendMemberSerializer, 
    ReactivateMemberSerializer, AdminDocumentSerializer, 
    ApproveDocumentSerializer, RejectDocumentSerializer
)
from .services import MemberManagementService, DocumentManagementService
from .models import MembershipStatus, DocumentStatus


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