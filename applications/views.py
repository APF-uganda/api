from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import Application, Document
from .serializers import ApplicationSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling membership application submissions.
    
    Endpoints:
    - POST /api/applications/ - Submit a new application (public)
    - GET /api/applications/ - List all applications (admin only)
    - GET /api/applications/{id}/ - Retrieve specific application (admin only)
    
    Requirements: 9.2, 9.5, 10.5
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get_permissions(self):
        """
        Allow anyone to create applications (POST).
        Require admin authentication for list and retrieve (GET).
        """
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser()]
    
    def create(self, request, *args, **kwargs):
        """
        Handle POST /api/applications/ for application submission.
        
        Accepts multipart/form-data with application fields and file uploads.
        Creates Application record with status 'pending' and associates uploaded documents.
        
        Returns:
        - 201 Created: Application successfully created
        - 400 Bad Request: Validation errors with specific field messages
        - 409 Conflict: Duplicate email/username
        
        Requirements: 9.2, 9.5, 10.5
        """
        # Extract application data from request
        serializer = self.get_serializer(data=request.data)
        
        try:
            # Validate application data
            serializer.is_valid(raise_exception=True)
            
            # Save application (status defaults to 'pending')
            application = serializer.save()
            
            # Handle file uploads if present
            uploaded_files = request.FILES.getlist('documents')
            for uploaded_file in uploaded_files:
                Document.objects.create(
                    application=application,
                    file=uploaded_file,
                    file_name=uploaded_file.name,
                    file_size=uploaded_file.size,
                    file_type=uploaded_file.content_type
                )
            
            # Return success response with created application data
            response_serializer = self.get_serializer(application)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            # Handle unique constraint violations (duplicate email/username)
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                error_message = {}
                if 'email' in str(e).lower():
                    error_message['email'] = ['This email is already registered.']
                if 'username' in str(e).lower():
                    error_message['username'] = ['This username is already taken.']
                
                return Response(
                    {'errors': error_message},
                    status=status.HTTP_409_CONFLICT
                )
            
            # Re-raise other exceptions to be handled by DRF's exception handler
            raise
    
    def list(self, request, *args, **kwargs):
        """
        Handle GET /api/applications/ for listing all applications.
        
        Admin only endpoint.
        Returns list of all applications ordered by submission date (newest first).
        
        Requirements: 9.2
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Handle GET /api/applications/{id}/ for retrieving specific application.
        
        Admin only endpoint.
        Returns detailed view of a single application including documents.
        
        Requirements: 9.2
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
