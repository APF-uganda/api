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

        document.file = uploaded_file
        document.file_name = uploaded_file.name
        document.file_size = uploaded_file.size
        document.file_type = uploaded_file.content_type or ''
        document.save(update_fields=['file', 'file_name', 'file_size', 'file_type'])

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

        document.delete()
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
