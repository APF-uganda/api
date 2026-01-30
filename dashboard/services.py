from applications.models import Application
from authentication.models import User, UserRole

def get_total_applications():
    return Application.objects.count()



def get_total_members():
    return Application.objects.filter(status='approved').count()

