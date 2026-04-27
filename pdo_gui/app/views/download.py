import os

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .. import pdo_runner
from ..models import Policy, User, VerifiableCredential


@require_http_methods(['POST'])
def download_data(request, pk):
    policy = get_object_or_404(Policy, pk=pk)

    active_user_id = request.session.get('active_user_id')
    if not active_user_id:
        return JsonResponse(
            {'success': False, 'error': 'No active user selected. Please choose a user in the navbar.'},
            status=400,
        )

    try:
        user = User.objects.get(pk=active_user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Active user not found.'}, status=404)

    try:
        vcs = VerifiableCredential.objects.filter(user=user).select_related('signature_authority')
        combined_vc = {vc.signature_authority.signing_context: vc.vc for vc in vcs}

        if not combined_vc:
            return JsonResponse(
                {'success': False, 'error': f'No verifiable credentials found for {user.name}'},
                status=400,
            )

        output_dir = os.path.join(settings.DOWNLOADS_DIR, policy.name, user.name)

        encrypted_path, decrypted_path = pdo_runner.issue_and_download(
            policy.name, combined_vc, output_dir
        )

        channel_private_key_path = os.path.join(settings.CHANNEL_KEYS_DIR, user.name, 'private_key.pem')
        if not os.path.exists(channel_private_key_path):
            return JsonResponse(
                {'success': False, 'error': f'Channel key not found for {user.name}'},
                status=400,
            )

        pdo_runner.decrypt_data(encrypted_path, channel_private_key_path, decrypted_path)

        return JsonResponse({'success': True, 'data_path': decrypted_path})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def get_channel_public_key(request, user_id):
    """Return the channel RSA public key for a user (used to pre-fill credential forms)."""
    user = get_object_or_404(User, pk=user_id)
    key_path = os.path.join(settings.CHANNEL_KEYS_DIR, user.name, 'public_key.pem')

    if not os.path.exists(key_path):
        return JsonResponse({'key': None})

    with open(key_path, 'r') as f:
        key = f.read()

    return JsonResponse({'key': key})
