"""
Custom permission classes for role-based access control (RBAC)
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticated(BasePermission):
    """
    Permission class that requires user to be authenticated.
    Works with JWT authentication.
    """
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAdmin(BasePermission):
    """
    Permission class that requires user to be authenticated and have admin role.
    Admin role is identified by role='1'
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == '1'
        )


class IsMember(BasePermission):
    """
    Permission class that requires user to be authenticated and have member role.
    Member role is identified by role='2'
    Also blocks suspended members (is_active=False) from accessing member resources.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated and has member role
        if not (request.user and request.user.is_authenticated and request.user.role == '2'):
            return False
        
        # Block suspended members from accessing member resources
        # Suspended members have is_active=False
        if not request.user.is_active:
            return False
        
        return True


class IsAdminOrMember(BasePermission):
    """
    Permission class that requires user to be authenticated and have either admin or member role.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['1', '2']
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Permission class that allows:
    - Admins to access any object
    - Users to access only their own objects
    
    Requires the object to have a 'user' field.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.role == '1':
            return True
        
        # Check if object has user field and if it matches the requesting user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # If no user field, deny access
        return False


class IsAdminOrReadOnly(BasePermission):
    """
    Permission class that allows:
    - Anyone to read (GET, HEAD, OPTIONS)
    - Only admins to write (POST, PUT, PATCH, DELETE)
    """
    
    def has_permission(self, request, view):
        # Allow read operations for everyone
        if request.method in SAFE_METHODS:
            return True
        
        # Write operations require admin
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == '1'
        )


class AllowPublicApplicationSubmission(BasePermission):
    """
    Special permission for application submissions:
    - Allow unauthenticated POST (create) for public application submission
    - Require admin authentication for all other operations
    """
    
    def has_permission(self, request, view):
        # Allow POST (create) for everyone
        if request.method == 'POST' and view.action == 'create':
            return True
        
        # All other operations require admin
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == '1'
        )


class AllowPublicContactSubmission(BasePermission):
    """
    Special permission for contact form submissions:
    - Allow unauthenticated POST for public contact submission
    - Require admin authentication for listing/viewing messages
    """
    
    def has_permission(self, request, view):
        # Allow POST for everyone (contact form submission)
        if request.method == 'POST':
            return True
        
        # All other operations (GET list) require admin
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == '1'
        )
