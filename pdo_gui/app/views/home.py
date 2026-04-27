from django.shortcuts import render

from ..models import SignatureAuthority, Policy, User


def index(request):
    context = {
        'signature_authorities': SignatureAuthority.objects.select_related('user').all(),
        'policies': Policy.objects.select_related('user').all(),
    }
    return render(request, 'index.html', context)
