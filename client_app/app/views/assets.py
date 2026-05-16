import json
import logging

from django.shortcuts import get_object_or_404, render

from .. import pdo_runner, registry_client
from ..did_utils import make_did, parse_did
from ..models import AppConfig, Entity
from ._helpers import BaseView, redirect_with_msg

logger = logging.getLogger(__name__)


def _guardian_url_port(host, port):
    """Compose the canonical guardian URL the download token contract stores."""
    return f"http://{host}:{port}"


class AssetsListView(BaseView):
    """GET: list all assets in the registry, annotated with local entity info."""

    def get(self, request):
        assets = []
        list_error = None
        try:
            assets = registry_client.list_assets()
            local_map = {e.did: e for e in Entity.objects.filter(entity_type='ASSET')}
            for a in assets:
                e = local_map.get(a['did'])
                a['is_local'] = e is not None
                a['local_pk'] = e.pk if e else None
        except Exception as e:
            logger.exception("Failed to fetch assets")
            list_error = str(e)

        wallets = Entity.objects.filter(entity_type='WALLET').order_by('pk')
        return render(request, 'assets/list.html', {
            'assets': assets,
            'wallets': wallets,
            'list_error': list_error,
            'use_result': request.session.pop('last_use_result', None),
        })


class AssetSetupView(BaseView):
    """GET: registration form. POST: register an asset.

    Each asset still gets its own identity contract so it has a stable DID
    in the registry. The policy/token contracts are only created later, in
    the expose flow.
    """

    def get(self, request):
        return render(request, 'assets/setup.html')

    def post(self, request):
        name = (request.POST.get('name') or '').strip()
        data_source = (request.POST.get('data_source') or '').strip()
        guardian_url = (request.POST.get('guardian_url') or '').strip()
        guardian_port = (request.POST.get('guardian_port') or '').strip()

        if not all([name, data_source, guardian_url, guardian_port]):
            return render(request, 'assets/setup.html', {
                'form': request.POST,
                'error': 'All fields are required.',
            })

        config = AppConfig.get_instance()
        user_name = config.public_key

        try:
            contract_id = pdo_runner.create_wallet(name, user_name)
            did = make_did(contract_id)

            Entity.objects.create(
                did=did,
                name=name,
                entity_type='ASSET',
                contract_name=f'identity.{name}.wallet',
                owner_key=user_name,
                extra_data={'guardian_url': guardian_url, 'guardian_port': guardian_port},
            )

            registry_asset = registry_client.register_asset(
                name=name, did=did,
                metadata={
                    'guardian_url': guardian_url,
                    'guardian_port': guardian_port,
                    'data_source': data_source,
                },
            )

            registry_pk = registry_asset['id']
            asset_registry_url = (
                f"{config.asset_registry_url.rstrip('/')}/api/assets/{registry_pk}/"
            )
            registry_client.update_asset_metadata(
                registry_pk, {'asset_registry_url': asset_registry_url})

        except Exception as e:
            logger.exception("Failed to register asset")
            return render(request, 'assets/setup.html', {
                'form': request.POST,
                'error': f'Failed to register asset: {e}',
            })

        return redirect_with_msg('/', f'Asset "{name}" registered.', 'success')


class AssetExposeView(BaseView):
    """GET: expose form. POST: create policy + token contracts and update registry."""

    def get(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk, entity_type='ASSET')

        templates = []
        templates_error = None
        try:
            templates = registry_client.list_policy_templates()
        except Exception as e:
            logger.exception("Failed to fetch policy templates")
            templates_error = str(e)

        return render(request, 'assets/expose.html', {
            'entity': entity,
            'templates': templates,
            'templates_error': templates_error,
            'expose_result': request.session.pop('last_expose_result', None),
        })

    def post(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk, entity_type='ASSET')
        user_name = AppConfig.get_instance().public_key
        url = f'/assets/{pk}/expose/'

        policy_data_raw = (request.POST.get('policy_data') or '').strip()
        try:
            policy_data = json.loads(policy_data_raw) if policy_data_raw else {}
        except json.JSONDecodeError as e:
            return redirect_with_msg(url, f'Invalid policy data JSON: {e}', 'error')

        guardian_host = entity.extra_data.get('guardian_url', '')
        guardian_port = entity.extra_data.get('guardian_port', '')
        if not guardian_host:
            try:
                meta = (registry_client.get_asset_by_did(entity.did) or {}).get('metadata', {}) or {}
                guardian_host = meta.get('guardian_url', '')
                guardian_port = meta.get('guardian_port', '')
            except Exception:
                pass

        if not guardian_host or not guardian_port:
            return redirect_with_msg(
                url, 'Guardian URL/port missing on this asset.', 'error')

        guardian = _guardian_url_port(guardian_host, guardian_port)

        try:
            result = pdo_runner.create_asset_policy(
                f'Policy for {entity.name}', guardian, user_name)

            if policy_data:
                pdo_runner.set_policy_data(
                    result['policy_contract_id'], policy_data, user_name)

            entity.extra_data.update({
                'policy_contract_id': result['policy_contract_id'],
                'token_contract_id': result['token_contract_id'],
                'guardian_url': guardian_host,
                'guardian_port': guardian_port,
            })
            entity.save(update_fields=['extra_data'])

            token_did = make_did(result['token_contract_id'])
            registry_client.update_asset_metadata_by_did(
                entity.did,
                {'policy_contract': token_did, 'policy_data': policy_data},
            )

        except Exception as e:
            logger.exception("Failed to expose asset")
            return redirect_with_msg(url, f'Failed to expose asset: {e}', 'error')

        request.session['last_expose_result'] = json.dumps({
            'policy_contract_id': result['policy_contract_id'],
            'token_contract_id': result['token_contract_id'],
            'token_did': token_did,
        }, indent=2)
        return redirect_with_msg(url, 'Asset exposed via download policy.', 'success')


class AssetUseView(BaseView):
    """POST-only: use an asset by exchanging a wallet's VP for a download credential."""

    def post(self, request):
        asset_did = (request.POST.get('asset_did') or '').strip()
        wallet_pk = request.POST.get('wallet_pk')

        if not asset_did or not wallet_pk:
            return redirect_with_msg('/', 'asset_did and wallet_pk are required.', 'error')

        wallet = get_object_or_404(Entity, pk=wallet_pk, entity_type='WALLET')
        user_name = AppConfig.get_instance().public_key

        try:
            asset_info = registry_client.get_asset_by_did(asset_did)
            metadata = asset_info.get('metadata', {}) or {}

            token_did = metadata.get('policy_contract', '')
            if not token_did:
                return redirect_with_msg(
                    '/', 'Asset has not been exposed (no policy_contract in registry).',
                    'error')
            token_contract_id, _ = parse_did(token_did)
            wallet_id, _ = parse_did(wallet.did)
            guardian = _guardian_url_port(
                metadata.get('guardian_url', ''),
                metadata.get('guardian_port', ''),
            )

            output_path, issued_vc = pdo_runner.use_asset(
                wallet_id=wallet_id,
                token_id=token_contract_id,
                guardian_url_port=guardian,
                user_name=user_name,
            )

        except Exception as e:
            logger.exception("Failed to use asset")
            return redirect_with_msg('/', f'Failed to use asset: {e}', 'error')

        request.session['last_use_result'] = json.dumps({
            'output_file': output_path,
            'issued_vc': issued_vc,
        }, indent=2)
        return redirect_with_msg('/', f'Downloaded asset to {output_path}.', 'success')
