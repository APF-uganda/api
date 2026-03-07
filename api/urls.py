"""
URL configuration for api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'message': 'APF Backend API is running',
        'endpoints': {
            'admin': '/admin/',
            'auth': '/api/v1/auth/',
            'contacts': '/api/v1/contacts/',
            'applications': '/api/v1/applications/',
            'payments': '/api/v1/payments/',
            'docs': '/api/docs/'
        }
    })

def secure_media_serve(request, path):
    """
    Serve media files with authentication check for application and member documents
    """
    from django.http import FileResponse, HttpResponseForbidden, Http404, JsonResponse
    from rest_framework_simplejwt.authentication import JWTAuthentication
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check if the path is for application or member documents (requires auth)
    requires_auth = path.startswith('application_documents/') or path.startswith('member_documents/')
    
    if requires_auth:
        # Authenticate the request
        jwt_auth = JWTAuthentication()
        try:
            auth_result = jwt_auth.authenticate(request)
            if auth_result is None:
                logger.warning(f"Unauthenticated access attempt to: {path}")
                return HttpResponseForbidden("Authentication required")
            user, token = auth_result
            
            # For application documents, allow admin or the document owner
            if path.startswith('application_documents/'):
                if user.role == '1':
                    pass  # Admin can access all
                else:
                    # Check if document belongs to this user's application
                    from Documents.models import Document
                    filename = path.split('/')[-1]
                    owns_doc = Document.objects.filter(
                        file__endswith=filename,
                        application__user=user
                    ).exists()
                    if not owns_doc:
                        logger.warning(f"User {user.email} attempted to access: {path}")
                        return HttpResponseForbidden("Access denied")
            
            # For member documents, allow access to own documents or admin
            elif path.startswith('member_documents/'):
                # Extract user_id from path (format: member_documents/user_123/...)
                path_parts = path.split('/')
                if len(path_parts) >= 2:
                    folder_name = path_parts[1]  # e.g., "user_123"
                    if folder_name.startswith('user_'):
                        doc_user_id = folder_name.replace('user_', '')
                        # Allow if admin or if accessing own documents
                        if not (user.role == '1' or str(user.id) == doc_user_id):
                            logger.warning(f"User {user.email} attempted to access another user's documents: {path}")
                            return HttpResponseForbidden("Access denied")
                
        except Exception as e:
            logger.error(f"Authentication error for {path}: {str(e)}")
            return HttpResponseForbidden("Invalid authentication")
    
    # Construct the full file path
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        logger.error(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        logger.error(f"Requested path: {path}")
        
        # Return JSON error for API requests
        if request.headers.get('Accept') == 'application/json' or 'api' in request.path:
            return JsonResponse({
                'error': 'File not found',
                'message': f'The requested file does not exist on the server.',
                'path': path
            }, status=404)
        
        raise Http404(f"File not found: {path}")
    
    # Serve the file
    try:
        return FileResponse(open(file_path, 'rb'))
    except Exception as e:
        logger.error(f"Error serving file {file_path}: {str(e)}")
        return JsonResponse({
            'error': 'Error serving file',
            'message': str(e)
        }, status=500)

# API v1 URL patterns (for Swagger to scan)
api_v1_patterns = [
    path("contacts/", include("contacts.urls")),
    path("applications/", include("applications.urls")),
    path("auth/", include("authentication.urls")),
    path("payments/", include("payments.urls")),
    path("documents/", include("Documents.urls")),
    path("reports/", include("reports.urls")),
    path("forum/", include("adminForum.urls")),
    path("notifications/", include("notifications.urls")),
    path("admin-management/", include("admin_management.urls")),
]

# Swagger/OpenAPI Schema - configured to scan only v1 patterns
schema_view = get_schema_view(
    openapi.Info(
        title="APF Portal API",
        default_version='v1',
        description="""
        API documentation for the APF Portal Backend.
        
        ## Authentication Flow
        1. Login with email/password to receive OTP
        2. Verify OTP to receive JWT tokens
        3. Use access token in Authorization header: `Bearer <token>`
        4. Refresh token when access token expires
        
        ## Base URL
        All API endpoints are prefixed with `/api/v1/`
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@apfportal.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[path("api/v1/", include(api_v1_patterns))],
)

urlpatterns = [
    
    path("", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    
    # Swagger/OpenAPI Documentation
    path("api/docs/", schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path("api/redoc/", schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # API v1 endpoints - organized by app
    path("api/v1/auth/", include("authentication.urls")),
    path("api/v1/contacts/", include("contacts.urls")),
    path("api/v1/applications/", include("applications.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/documents/", include("Documents.urls")),
    path("api/v1/reports/", include("reports.urls")),
    path("api/v1/forum/", include("adminForum.urls")),
    path("api/v1/notifications/", include("notifications.urls")),  # Notifications + Announcements
    path("api/v1/admin-management/", include("admin_management.urls")),
    
    # Secure media files serving
    path("media/<path:path>", secure_media_serve, name="secure-media"),
]

# Serve media files in development (fallback for non-authenticated access)
# The secure_media_serve view above will handle authentication for sensitive files
if settings.DEBUG and settings.MEDIA_URL and settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
