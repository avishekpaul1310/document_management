from .models import Notification

def notification_count(request):
    """
    Context processor to add notification count to all templates
    """
    count = 0
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return {
        'notification_count': count
    }