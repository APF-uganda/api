from applications.models import Application

def get_total_applications():
    return Application.objects.count
