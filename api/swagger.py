"""
Custom Swagger/OpenAPI schema inspector that normalizes auto-generated tags
so that all endpoints under a given URL prefix share a single, properly-cased
Swagger section.
"""

from drf_yasg.inspectors import SwaggerAutoSchema


# Map the lowercase auto-generated tag (derived from URL prefix) to the
# canonical tag name you want displayed in the docs.
TAG_MAP = {
    'applications': 'Applications',
    'auth': 'Authentication',
    'profile': 'Authentication',  # Move profile endpoints to Authentication section
    'contacts': 'Contacts',
    'payments': 'Payments',
    'payments-admin': 'Payments',  # Move payments-admin to Payments section
    'documents': 'Documents',
    'reports': 'Reports',
    'forum': 'Forum',
    'notifications': 'Notifications',
    'announcements': 'Notifications',  # Move announcements to Notifications section
    'admin-management': 'Admin Management',
}


class CustomAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        tags = super().get_tags(operation_keys)
        # Replace any auto-generated lowercase tag with its canonical form
        return [TAG_MAP.get(t, t) for t in tags]
