import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .. import pdo_runner
from ..models import CredentialTemplate, Policy, PolicyTemplate, PolicyTrustedAuthority, SignatureAuthority, User


def create(request):
    policy_templates = PolicyTemplate.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        guardian_url = request.POST.get('guardian_url', '').strip()
        guardian_port_raw = request.POST.get('guardian_port', '').strip()
        template_id = request.POST.get('template_id')

        active_user_id = request.session.get('active_user_id')
        if not active_user_id:
            return render(request, 'policy_create.html', {
                'policy_templates': policy_templates,
                'error': 'No active user selected. Please choose a user in the navbar.',
            })

        try:
            guardian_port = int(guardian_port_raw)
            user = User.objects.get(pk=active_user_id)
            template = PolicyTemplate.objects.get(pk=template_id) if template_id else None
            pdo_runner.create_policy(name, user.name, description, guardian_url, guardian_port)

            policy = Policy.objects.create(
                user=user,
                template=template,
                name=name,
                description=description,
                guardian_url=guardian_url,
                guardian_port=guardian_port,
            )
            return redirect('policy_dashboard', pk=policy.pk)

        except ValueError:
            error = 'Guardian port must be a valid integer.'
        except Exception as e:
            error = str(e)

        return render(request, 'policy_create.html', {'policy_templates': policy_templates, 'error': error})

    return render(request, 'policy_create.html', {'policy_templates': policy_templates})


def dashboard(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    trusted_authorities = (
        PolicyTrustedAuthority.objects
        .filter(policy=policy)
        .select_related('signature_authority')
    )
    context = {
        'policy': policy,
        'signature_authorities': SignatureAuthority.objects.all(),
        'credential_templates': CredentialTemplate.objects.all(),
        'trusted_authorities': trusted_authorities,
        'policy_data_json': json.dumps(policy.policy_data, indent=2) if policy.policy_data else '',
    }
    return render(request, 'policy_dashboard.html', context)


@require_http_methods(['POST'])
def register_authority(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    sa_id = request.POST.get('signature_authority_id')
    credential_type = request.POST.get('credential_type', '').strip()

    try:
        sa = SignatureAuthority.objects.get(pk=sa_id)
        pdo_runner.register_trusted_authority(
            policy.name, sa.name, sa.signing_context, credential_type
        )
        PolicyTrustedAuthority.objects.create(
            policy=policy,
            signature_authority=sa,
            credential_type=credential_type,
        )
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(['POST'])
def set_policy_data(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    policy_data_raw = request.POST.get('policy_data', '')

    try:
        policy_data = json.loads(policy_data_raw)
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'Invalid JSON: {e}'}, status=400)

    try:
        pdo_runner.set_policy_data(policy.name, policy_data)
        policy.policy_data = policy_data
        policy.save()
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
