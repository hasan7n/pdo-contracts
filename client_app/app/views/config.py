import logging

from django.shortcuts import render
from django.views.generic import View

from ..identity import set_current_identity
from ..models import AppConfig
from ._helpers import redirect_with_msg

logger = logging.getLogger(__name__)


class ConfigPageView(View):
    """GET shows the config form; POST saves and redirects."""

    template_name = 'config.html'

    def get(self, request):
        return render(request, self.template_name, {'config': AppConfig.get_instance()})

    def post(self, request):
        config = AppConfig.get_instance()
        for field in ('ledger_url', 'asset_registry_url', 'template_registry_url', 'public_key'):
            if field in request.POST:
                setattr(config, field, request.POST[field].strip())
        config.save()
        target = '/' if config.is_configured() else '/config/'
        return redirect_with_msg(target, 'Configuration saved.', 'success')


class IdentitySetView(View):
    """POST-only: change the current identity from the navbar modal."""

    def post(self, request):
        public_key = (request.POST.get('public_key') or '').strip()
        referer = request.META.get('HTTP_REFERER', '/')
        if not public_key:
            return redirect_with_msg(referer, 'public_key is required', 'error')
        set_current_identity(public_key)
        return redirect_with_msg(referer, f'Identity set to {public_key}.', 'success')
