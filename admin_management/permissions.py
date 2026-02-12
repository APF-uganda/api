from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Custom permission class that checks if the user has admin role.
    Admin role is identified by role='1' in the User model.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated and has admin role
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == '1'  # Admin role
        )
    
    def has_object_permission(self, request, view, obj):
        # For object-level permissions, check if user is admin
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == '1'  # Admin role
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Permission class that allows:
    - Anyone to read (GET, HEAD, OPTIONS) 
    - Only admins to write (POST, PUT, PATCH, DELETE)
    """
    
    def has_permission(self, request, view):
        # Allow read operations for everyone
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write operations require admin
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == '1'  # Admin role
        )