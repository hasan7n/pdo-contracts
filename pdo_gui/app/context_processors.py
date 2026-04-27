from .models import User


def active_user(request):
    active_user_id = request.session.get('active_user_id')
    users = list(User.objects.all())
    active = None
    if active_user_id:
        try:
            active = User.objects.get(pk=active_user_id)
        except User.DoesNotExist:
            pass
    return {
        'all_users': users,
        'active_user': active,
    }
