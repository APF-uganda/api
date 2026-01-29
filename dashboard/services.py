from applications.models import Application
from authentication.models import User, UserRole

def get_total_applications():
    return Application.objects.count


def get_total_members():
    """
    Returns the total number of active members.
    A member is defined as a user with role=MEMBER.
    """
    return User.objects.filter(
        role=UserRole.MEMBER,
        is_active=True
    ).count()
