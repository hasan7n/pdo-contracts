import json
import logging

from django.shortcuts import get_object_or_404, render

from .. import pdo_runner, registry_client
from ..did_utils import make_did, parse_did
from ..models import AppConfig, Entity
from ._helpers import BaseView, redirect_with_msg

logger = logging.getLogger(__name__)


class IssuersListView(BaseView):
    """GET: list issuers. POST: create a new issuer."""

    def get(self, request):
        issuers = Entity.objects.filter(entity_type='ISSUER').order_by('pk')
        return render(request, 'issuers/list.html', {'issuers': issuers})

    def post(self, request):
        name = (request.POST.get('name') or '').strip()
        description = (request.POST.get('description') or '').strip()
        if not name:
            return redirect_with_msg('/issuers/', 'Issuer name is required.', 'error')

        user_name = AppConfig.get_instance().public_key
        try:
            contract_id = pdo_runner.create_issuer(name, user_name, description)
        except Exception as e:
            logger.exception("Failed to create issuer")
            return redirect_with_msg('/issuers/', f'Failed to create issuer: {e}', 'error')

        Entity.objects.create(
            did=make_did(contract_id),
            name=name,
            entity_type='ISSUER',
            contract_name=f'identity.{name}.signature_authority',
            owner_key=user_name,
        )
        return redirect_with_msg('/issuers/', f'Issuer "{name}" created.', 'success')


class IssuerDetailView(BaseView):
    """GET: show issuer info + credential templates. POST: issue a VC."""

    def get(self, request, pk):
        issuer = get_object_or_404(Entity, pk=pk, entity_type='ISSUER')

        templates = []
        templates_error = None
        try:
            templates = registry_client.list_credential_templates()
        except Exception as e:
            logger.exception("Failed to fetch credential templates")
            templates_error = str(e)

        return render(request, 'issuers/detail.html', {
            'entity': issuer,
            'templates': templates,
            'templates_error': templates_error,
            'signed_vc': request.session.pop('last_signed_vc', None),
        })

    def post(self, request, pk):
        issuer = get_object_or_404(Entity, pk=pk, entity_type='ISSUER')
        user_name = AppConfig.get_instance().public_key
        url = f'/issuers/{pk}/'

        template_type = (request.POST.get('template_type') or '').strip()
        subject_did = (request.POST.get('subject_did') or '').strip()
        claims_raw = (request.POST.get('claims') or '').strip()

        if not template_type or not subject_did:
            return redirect_with_msg(
                url, 'Template type and subject DID are required.', 'error')

        try:
            claims = json.loads(claims_raw) if claims_raw else {}
        except json.JSONDecodeError as e:
            return redirect_with_msg(url, f'Invalid claims JSON: {e}', 'error')

        sa_contract_id, _ = parse_did(issuer.did)
        subject_contract_id, _ = parse_did(subject_did)
        credential = {
            'type': [template_type],
            'issuer': {'id': sa_contract_id},
            'credentialSubject': {'id': subject_contract_id, 'claims': claims},
        }

        try:
            signed_vc = pdo_runner.sign_credential(
                sa_contract_id, signing_context=issuer.name,
                credential_dict=credential, user_name=user_name)
        except Exception as e:
            logger.exception("Failed to issue VC")
            return redirect_with_msg(url, f'Failed to issue VC: {e}', 'error')

        request.session['last_signed_vc'] = json.dumps(signed_vc, indent=2)
        return redirect_with_msg(url, 'Credential issued.', 'success')
