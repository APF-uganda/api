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
            'dashboard': '/api/v1/',
            'docs': '/api/docs/'
        }
    })

# API v1 URL patterns (for Swagger to scan)
api_v1_patterns = [
    path("contacts/", include("contacts.urls")),
    path("applications/", include("applications.urls")),
    path("auth/", include("authentication.urls")),
    path("payments/", include("payments.urls")),
    path("", include("dashboard.urls")),
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
    
    # API v1 endpoints
    path("api/v1/contacts/", include("contacts.urls")),
    path("api/v1/", include("applications.urls")),
    path("api/v1/auth/", include("authentication.urls")),
    path("api/v1/", include("dashboard.urls")),
    path("api/v1/", include("profiles.urls")),
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    path("api/v1/reports/", include("reports.urls")),
    path("api/v1/forum/", include("adminForum.urls")),
    path("api/v1/notifications/", include("AdminNotifications.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/", include(api_v1_patterns)),
]

# Serve media files in development
if settings.MEDIA_URL and settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
