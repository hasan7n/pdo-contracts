from urllib.parse import urlencode

from django.shortcuts import redirect
from django.views.generic.base import View

from ..models import AppConfig


class ConfiguredRequiredMixin:
    """Mixin that redirects to /config/ if the app has not been configured yet.

    Mixin into class-based views so that page handlers don't have to repeat
    the configuration check. Place this BEFORE View in the MRO.
    """

    def dispatch(self, request, *args, **kwargs):
        if not AppConfig.get_instance().is_configured():
            return redirect('/config/')
        return super().dispatch(request, *args, **kwargs)


class BaseView(ConfiguredRequiredMixin, View):
    """Convenience base for app pages that require configuration."""
    pass


def redirect_with_msg(url, msg, msg_type='info'):
    """Redirect to ``url`` with ``?msg=...&msg_type=...`` appended.

    The base template has a small JS shim that reads these params on page
    load, shows the message via ``alert(...)``, then strips them from the
    URL via ``history.replaceState`` so a refresh doesn't repeat them.
    """
    sep = '&' if '?' in url else '?'
    return redirect(f"{url}{sep}{urlencode({'msg': msg, 'msg_type': msg_type})}")
