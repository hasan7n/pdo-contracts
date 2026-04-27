from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from ..models import User


@require_http_methods(['POST'])
def set_active_user(request):
    user_id = request.POST.get('user_id')
    try:
        user = User.objects.get(pk=user_id)
        request.session['active_user_id'] = user.pk
    except (User.DoesNotExist, TypeError, ValueError):
        request.session.pop('active_user_id', None)

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)
