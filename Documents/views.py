from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import action
from django.db.models import Q

from applications.models import Application
from .models import Document, MemberDocument
from .serializers import DocumentSerializer, MemberDocumentSerializer
from drf_yasg.utils import swagger_auto_schema


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

        if hasattr(document, 'status'):
            document.status = status_value
        if hasattr(document, 'admin_feedback') and feedback_value is not None:
            document.admin_feedback = feedback_value
        document.save()

        serializer = (
            MemberDocumentSerializer(document, context={'request': request})
            if doc_is_member
            else DocumentSerializer(document, context={'request': request})
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["documents"])
    @action(detail=True, methods=['patch'], url_path='approve', permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
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

        serializer = (
            MemberDocumentSerializer(document, context={'request': request})
            if doc_is_member
            else DocumentSerializer(document, context={'request': request})
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["documents"])
    @action(detail=True, methods=['patch'], url_path='reject', permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
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
