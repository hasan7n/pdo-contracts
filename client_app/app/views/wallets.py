import json
import logging

from django.shortcuts import get_object_or_404, render

from .. import pdo_runner
from ..did_utils import make_did, parse_did
from ..models import AppConfig, Entity
from ._helpers import BaseView, redirect_with_msg

logger = logging.getLogger(__name__)


class WalletsListView(BaseView):
    """GET: list wallets the user owns. POST: create a new wallet."""

    def get(self, request):
        wallets = Entity.objects.filter(entity_type='WALLET').order_by('pk')
        return render(request, 'wallets/list.html', {'wallets': wallets})

    def post(self, request):
        name = (request.POST.get('name') or '').strip()
        if not name:
            return redirect_with_msg('/wallets/', 'Wallet name is required.', 'error')

        user_name = AppConfig.get_instance().public_key
        try:
            contract_id = pdo_runner.create_wallet(name, user_name)
        except Exception as e:
            logger.exception("Failed to create wallet")
            return redirect_with_msg('/wallets/', f'Failed to create wallet: {e}', 'error')

        Entity.objects.create(
            did=make_did(contract_id),
            name=name,
            entity_type='WALLET',
            contract_name=f'identity.{name}.wallet',
            owner_key=user_name,
        )
        return redirect_with_msg('/wallets/', f'Wallet "{name}" created.', 'success')


class WalletDetailView(BaseView):
    """GET: show wallet info + stored VCs. POST: add a new VC."""

    def get(self, request, pk):
        wallet = get_object_or_404(Entity, pk=pk, entity_type='WALLET')
        user_name = AppConfig.get_instance().public_key

        vcs = {}
        vcs_error = None
        try:
            contract_id, _ = parse_did(wallet.did)
            vcs = pdo_runner.wallet_list_vcs(contract_id, user_name)
        except Exception as e:
            logger.exception("Failed to list wallet VCs")
            vcs_error = str(e)

        return render(request, 'wallets/detail.html', {
            'entity': wallet,
            'vcs': vcs,
            'vcs_error': vcs_error,
        })

    def post(self, request, pk):
        wallet = get_object_or_404(Entity, pk=pk, entity_type='WALLET')
        user_name = AppConfig.get_instance().public_key
        url = f'/wallets/{pk}/'

        vc_raw = (request.POST.get('vc_json') or '').strip()
        if not vc_raw:
            return redirect_with_msg(url, 'VC JSON is required.', 'error')
        try:
            vc = json.loads(vc_raw)
        except json.JSONDecodeError as e:
            return redirect_with_msg(url, f'Invalid JSON: {e}', 'error')

        try:
            contract_id, _ = parse_did(wallet.did)
            pdo_runner.wallet_add_vc(contract_id, vc, user_name)
        except Exception as e:
            logger.exception("Failed to add VC")
            return redirect_with_msg(url, f'Failed to add VC: {e}', 'error')

        return redirect_with_msg(url, 'Credential added.', 'success')
