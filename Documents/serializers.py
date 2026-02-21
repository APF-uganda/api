from rest_framework import serializers
from .models import Document, MemberDocument


class DocumentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='file_name', read_only=True)
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    uploadedDate = serializers.SerializerMethodField()
    expiryDate = serializers.SerializerMethodField()
    fileUrl = serializers.SerializerMethodField()
    adminFeedback = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id',
            'name',
            'type',
            'status',
            'uploadedDate',
            'expiryDate',
            'fileUrl',
            'adminFeedback',
        ]

    def get_type(self, obj):
        doc_type = (obj.document_type or '').upper()
        if doc_type in ('SYSTEM', 'USER'):
            return doc_type
        return 'USER'

    def get_status(self, obj):
        # Use model field if present; fallback to pending
        value = getattr(obj, 'status', None)
        return value if value else 'pending'

    def get_uploadedDate(self, obj):
        return obj.uploaded_at.date().isoformat() if obj.uploaded_at else ''

    def get_expiryDate(self, obj):
        return getattr(obj, 'expiry_date', None)

    def get_fileUrl(self, obj):
        if not obj.file:
            print(f"[DocumentSerializer] No file for document {obj.id}")
            return None
        request = self.context.get('request')
        if request:
            url = request.build_absolute_uri(obj.file.url)
            print(f"[DocumentSerializer] Generated URL for {obj.file_name}: {url}")
            return url
        print(f"[DocumentSerializer] No request context, using relative URL: {obj.file.url}")
        return obj.file.url

    def get_adminFeedback(self, obj):
        return getattr(obj, 'admin_feedback', None)


class MemberDocumentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='file_name', read_only=True)
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    uploadedDate = serializers.SerializerMethodField()
    expiryDate = serializers.SerializerMethodField()
    fileUrl = serializers.SerializerMethodField()
    adminFeedback = serializers.SerializerMethodField()

    class Meta:
        model = MemberDocument
        fields = [
            'id',
            'name',
            'type',
            'status',
            'uploadedDate',
            'expiryDate',
            'fileUrl',
            'adminFeedback',
        ]

    def get_type(self, _obj):
        return 'USER'

    def get_status(self, obj):
        return obj.status or 'pending'

    def get_uploadedDate(self, obj):
        return obj.uploaded_at.date().isoformat() if obj.uploaded_at else ''

    def get_expiryDate(self, obj):
        return obj.expiry_date

    def get_fileUrl(self, obj):
        if not obj.file:
            print(f"[MemberDocumentSerializer] No file for document {obj.id}")
            return None
        request = self.context.get('request')
        if request:
            url = request.build_absolute_uri(obj.file.url)
            print(f"[MemberDocumentSerializer] Generated URL for {obj.file_name}: {url}")
            return url
        print(f"[MemberDocumentSerializer] No request context, using relative URL: {obj.file.url}")
        return obj.file.url

    def get_adminFeedback(self, obj):
        return obj.admin_feedback or ''
