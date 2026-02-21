from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from django.db.models import Q

from applications.models import Application
from .models import Document, MemberDocument
from .serializers import DocumentSerializer, MemberDocumentSerializer
from drf_yasg.utils import swagger_auto_schema


@swagger_auto_schema(method='get', tags=["documents"])
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def get_member_documents(request, user_id):
    """
    Admin-only: Get all documents for a specific member.
    Returns both application documents and member-uploaded documents.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    print(f"[Documents] Fetching documents for user_id: {user_id}")
    
    try:
        user = User.objects.get(id=user_id, role='2')  # Ensure it's a member
        print(f"[Documents] Found user: {user.email}")
    except User.DoesNotExist:
        print(f"[Documents] User not found: {user_id}")
        return Response(
            {'error': {'message': 'Member not found.'}},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get application documents
    app_docs = Document.objects.filter(application__user=user)
    print(f"[Documents] Found {app_docs.count()} application documents")
    
    # Get member documents
    member_docs = MemberDocument.objects.filter(user=user)
    print(f"[Documents] Found {member_docs.count()} member documents")
    
    # Serialize both types
    app_data = DocumentSerializer(app_docs, many=True, context={'request': request}).data
    member_data = MemberDocumentSerializer(member_docs, many=True, context={'request': request}).data
    
    # Combine and sort by upload date
    combined = list(app_data) + list(member_data)
    combined.sort(key=lambda item: item.get('uploadedDate', ''), reverse=True)
    
    print(f"[Documents] Returning {len(combined)} total documents")
    
    return Response({
        'user_id': user_id,
        'user_email': user.email,
        'user_name': f"{user.first_name} {user.last_name}".strip() or user.email,
        'total_documents': len(combined),
        'documents': combined
    }, status=status.HTTP_200_OK)


class DocumentViewSet(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    @swagger_auto_schema(tags=["documents"])
    def _get_user_application(self, user):
        return (
            Application.objects.filter(user=user)
            .order_by('-submitted_at')
            .first()
        )
    
    @swagger_auto_schema(tags=["documents"])
    def list(self, request):
        app_docs = Document.objects.filter(application__user=request.user)
        member_docs = MemberDocument.objects.filter(user=request.user)

        doc_type = (request.query_params.get('type') or '').upper()
        if doc_type in ('SYSTEM', 'USER'):
            if doc_type == 'SYSTEM':
                member_docs = MemberDocument.objects.none()
                app_docs = app_docs.filter(document_type__iexact='SYSTEM')
            else:
                app_docs = app_docs.filter(document_type__iexact='USER')

        app_data = DocumentSerializer(app_docs, many=True, context={'request': request}).data
        member_data = MemberDocumentSerializer(member_docs, many=True, context={'request': request}).data
        combined = list(app_data) + list(member_data)
        combined.sort(key=lambda item: item.get('uploadedDate', ''), reverse=True)
        return Response(combined, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(tags=["documents"])
    def create(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'error': {'message': 'File is required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        doc_type = (request.data.get('type') or request.data.get('document_type') or 'USER').upper()

        document = MemberDocument.objects.create(
            user=request.user,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_type=uploaded_file.content_type or '',
            document_type=doc_type,
        )

        # Create activity notification
        try:
            from notifications.models import UserNotification
            UserNotification.objects.create(
                user=request.user,
                title="Document Uploaded",
                message=f'You uploaded "{uploaded_file.name}" for admin review.',
                notification_type="success",
                priority="low"
            )
        except Exception as e:
            print(f"Failed to create notification: {e}")

        serializer = MemberDocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["documents"], methods=['put', 'patch'])
    @action(detail=True, methods=['put', 'patch'], url_path='replace')
    def replace(self, request, pk=None):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'error': {'message': 'File is required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        document = MemberDocument.objects.filter(pk=pk, user=request.user).first()
        if not document:
            return Response(
                {'error': {'message': 'Document not found.'}},
                status=status.HTTP_404_NOT_FOUND
            )

        # Store old document name
        old_name = document.file_name or 'Document'
        
        # Update document
        document.file = uploaded_file
        document.file_name = uploaded_file.name
        document.file_size = uploaded_file.size
        document.file_type = uploaded_file.content_type or ''
        
        # Reset status to pending for admin review
        if hasattr(document, 'status'):
            document.status = 'pending'
        
        document.save(update_fields=['file', 'file_name', 'file_size', 'file_type', 'status'])

        # Create activity notification
        try:
            from notifications.models import UserNotification
            UserNotification.objects.create(
                user=request.user,
                title="Document Replaced",
                message=f'You replaced "{old_name}" with "{uploaded_file.name}". It will be reviewed by admin.',
                notification_type="info",
                priority="low"
            )
        except Exception as e:
            print(f"Failed to create notification: {e}")

        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["documents"])
    def destroy(self, request, pk=None):
        document = MemberDocument.objects.filter(pk=pk, user=request.user).first()
        if not document:
            return Response(
                {'error': {'message': 'Document not found.'}},
                status=status.HTTP_404_NOT_FOUND
            )

        # Store document name before deletion
        document_name = document.file_name or 'Document'
        
        # Delete the document
        document.delete()
        
        # Create activity notification
        try:
            from notifications.models import UserNotification
            UserNotification.objects.create(
                user=request.user,
                title="Document Removed",
                message=f'You removed "{document_name}" from your documents.',
                notification_type="info",
                priority="low"
            )
        except Exception as e:
            # Log error but don't fail the delete operation
            print(f"Failed to create notification: {e}")
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["documents"])
    @action(detail=True, methods=['patch'], url_path='admin-review', permission_classes=[IsAdminUser])
    def admin_review(self, request, pk=None):
        """
        Admin-only: update status/feedback for a document.
        Sends notification to member when status changes.
        """
        status_value = (request.data.get('status') or '').lower()
        feedback_value = request.data.get('admin_feedback') or request.data.get('adminFeedback')

        if status_value not in ('approved', 'pending', 'rejected', 'expired'):
            return Response(
                {'error': {'message': 'Invalid status.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        document = MemberDocument.objects.filter(pk=pk).first()
        doc_is_member = document is not None
        if not document:
            document = Document.objects.filter(pk=pk).first()

        if not document:
            return Response(
                {'error': {'message': 'Document not found.'}},
                status=status.HTTP_404_NOT_FOUND
            )

        # Store old status to check if it changed
        old_status = getattr(document, 'status', None)
        
        if hasattr(document, 'status'):
            document.status = status_value
        if hasattr(document, 'admin_feedback') and feedback_value is not None:
            document.admin_feedback = feedback_value
        document.save()

        # Send notification if status changed
        if old_status != status_value:
            try:
                from notifications.models import UserNotification
                
                # Get the document owner
                doc_user = document.user if hasattr(document, 'user') else (document.application.user if hasattr(document, 'application') else None)
                
                if doc_user:
                    if status_value == 'approved':
                        UserNotification.objects.create(
                            user=doc_user,
                            title="Document Approved",
                            message=f'Your document "{document.file_name}" has been approved by admin.' + (f' Feedback: {feedback_value}' if feedback_value else ''),
                            notification_type='success',
                            priority='medium'
                        )
                        print(f"[Documents] Sent approval notification to {doc_user.email} for document {document.file_name}")
                    elif status_value == 'rejected':
                        UserNotification.objects.create(
                            user=doc_user,
                            title="Document Rejected",
                            message=f'Your document "{document.file_name}" has been rejected.' + (f' Reason: {feedback_value}' if feedback_value else ' Please upload a corrected version.'),
                            notification_type='warning',
                            priority='high'
                        )
                        print(f"[Documents] Sent rejection notification to {doc_user.email} for document {document.file_name}")
            except Exception as e:
                print(f"[Documents] Failed to send notification: {str(e)}")

        serializer = (
            MemberDocumentSerializer(document, context={'request': request})
            if doc_is_member
            else DocumentSerializer(document, context={'request': request})
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["documents"])
    @action(detail=True, methods=['patch'], url_path='approve', permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """
        Admin-only: Approve a document.
        Sends notification to member.
        """
        feedback_value = request.data.get('admin_feedback') or request.data.get('adminFeedback')

        document = MemberDocument.objects.filter(pk=pk).first()
        doc_is_member = document is not None
        if not document:
            document = Document.objects.filter(pk=pk).first()
        if not document:
            return Response({'error': {'message': 'Document not found.'}}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(document, 'status'):
            document.status = 'approved'
        if hasattr(document, 'admin_feedback') and feedback_value is not None:
            document.admin_feedback = feedback_value
        document.save()

        # Send notification
        try:
            from notifications.models import UserNotification
            doc_user = document.user if hasattr(document, 'user') else (document.application.user if hasattr(document, 'application') else None)
            
            if doc_user:
                UserNotification.objects.create(
                    user=doc_user,
                    title="Document Approved",
                    message=f'Your document "{document.file_name}" has been approved by admin.' + (f' Feedback: {feedback_value}' if feedback_value else ''),
                    notification_type='success',
                    priority='medium'
                )
                print(f"[Documents] Sent approval notification to {doc_user.email}")
        except Exception as e:
            print(f"[Documents] Failed to send notification: {str(e)}")

        serializer = (
            MemberDocumentSerializer(document, context={'request': request})
            if doc_is_member
            else DocumentSerializer(document, context={'request': request})
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["documents"])
    @action(detail=True, methods=['patch'], url_path='reject', permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """
        Admin-only: Reject a document.
        Sends notification to member.
        """
        feedback_value = request.data.get('admin_feedback') or request.data.get('adminFeedback')

        document = MemberDocument.objects.filter(pk=pk).first()
        doc_is_member = document is not None
        if not document:
            document = Document.objects.filter(pk=pk).first()
        if not document:
            return Response({'error': {'message': 'Document not found.'}}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(document, 'status'):
            document.status = 'rejected'
        if hasattr(document, 'admin_feedback') and feedback_value is not None:
            document.admin_feedback = feedback_value
        document.save()

        # Send notification
        try:
            from notifications.models import UserNotification
            doc_user = document.user if hasattr(document, 'user') else (document.application.user if hasattr(document, 'application') else None)
            
            if doc_user:
                UserNotification.objects.create(
                    user=doc_user,
                    title="Document Rejected",
                    message=f'Your document "{document.file_name}" has been rejected.' + (f' Reason: {feedback_value}' if feedback_value else ' Please upload a corrected version.'),
                    notification_type='warning',
                    priority='high'
                )
                print(f"[Documents] Sent rejection notification to {doc_user.email}")
        except Exception as e:
            print(f"[Documents] Failed to send notification: {str(e)}")

        serializer = (
            MemberDocumentSerializer(document, context={'request': request})
            if doc_is_member
            else DocumentSerializer(document, context={'request': request})
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["documents"])
    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """
        Download a document file.
        Members can only download their own documents.
        """
        from django.http import FileResponse, Http404
        import os

        # Try to find the document in MemberDocument first
        document = MemberDocument.objects.filter(pk=pk, user=request.user).first()
        
        # If not found, try Document (application documents)
        if not document:
            document = Document.objects.filter(pk=pk, application__user=request.user).first()
        
        if not document:
            return Response(
                {'error': {'message': 'Document not found or access denied.'}},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if file exists
        if not document.file:
            return Response(
                {'error': {'message': 'File not available.'}},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # Open the file
            file_handle = document.file.open('rb')
            
            # Get the filename
            filename = document.file_name or os.path.basename(document.file.name)
            
            # Create response with file
            response = FileResponse(file_handle, content_type=document.file_type or 'application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = document.file_size
            
            return response
            
        except Exception as e:
            return Response(
                {'error': {'message': f'Error downloading file: {str(e)}'}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
