import json
import os

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .. import pdo_runner
from ..models import CredentialTemplate, SignatureAuthority, User, VerifiableCredential


def create(request):
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('act_as')
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        try:
            user = User.objects.get(pk=user_id)
            pdo_runner.create_signature_authority(name, user.name, description)

            sa = SignatureAuthority.objects.create(
                user=user,
                name=name,
                description=description,
                signing_context=name,
            )
            return redirect('sa_dashboard', pk=sa.pk)

        except Exception as e:
            return render(request, 'signature_authority_create.html', {
                'users': users,
                'error': str(e),
            })

    return render(request, 'signature_authority_create.html', {'users': users})


def dashboard(request, pk):
    sa = get_object_or_404(SignatureAuthority, pk=pk)
    templates = CredentialTemplate.objects.all()
    vcs = VerifiableCredential.objects.filter(signature_authority=sa).select_related('user')

    # Build template data for JS consumption
    templates_data = {
        str(t.pk): {'type_': t.template_type, 'claims_keys': t.claims_keys}
        for t in templates
    }

    context = {
        'sa': sa,
        'users': User.objects.all(),
        'templates': templates,
        'templates_json': json.dumps(templates_data),
        'vcs': vcs,
    }
    return render(request, 'signature_authority_dashboard.html', context)


@require_http_methods(['POST'])
def sign_credential(request, pk):
    sa = get_object_or_404(SignatureAuthority, pk=pk)

    template_id = request.POST.get('template_id')
    subject_user_id = request.POST.get('subject_user_id')
    claims_json = request.POST.get('claims', '{}')

    try:
        template = CredentialTemplate.objects.get(pk=template_id)
        subject_user = User.objects.get(pk=subject_user_id)
        claims = json.loads(claims_json)

        credential = {
            "issuer": {"id": "pdo-gui-issuer"},
            "credentialSubject": {
                "subject": {"id": subject_user.did},
                "claims": claims,
            },
            "name": f"{template.template_type} credential",
            "description": f"{template.template_type} credential for {subject_user.name}",
        }

        os.makedirs(settings.SIGNED_CREDENTIALS_DIR, exist_ok=True)
        output_path = os.path.join(
            settings.SIGNED_CREDENTIALS_DIR,
            f'{sa.name}__{subject_user.name}__{template.template_type}.json',
        )

        pdo_runner.sign_credential(sa.name, sa.signing_context, credential, output_path)

        with open(output_path, 'r') as f:
            signed_vc = json.load(f)

        VerifiableCredential.objects.create(
            user=subject_user,
            signature_authority=sa,
            vc=signed_vc,
        )

        return JsonResponse({'success': True, 'message': f'Credential signed for {subject_user.name}'})

    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'Invalid claims JSON: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
