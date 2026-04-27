from django.urls import path

from .views import download, home, policy, signature_authority

urlpatterns = [
    path('', home.index, name='index'),

    # Signature Authority pages
    path('signature-authority/create/', signature_authority.create, name='sa_create'),
    path('signature-authority/<int:pk>/', signature_authority.dashboard, name='sa_dashboard'),
    path('signature-authority/<int:pk>/sign-credential/', signature_authority.sign_credential, name='sa_sign_credential'),

    # Policy pages
    path('policy/create/', policy.create, name='policy_create'),
    path('policy/<int:pk>/', policy.dashboard, name='policy_dashboard'),
    path('policy/<int:pk>/register-authority/', policy.register_authority, name='policy_register_authority'),
    path('policy/<int:pk>/set-policy-data/', policy.set_policy_data, name='policy_set_data'),

    # Download actions
    path('policy/<int:pk>/download/', download.download_data, name='download_data'),
    path('api/users/<int:user_id>/channel-public-key/', download.get_channel_public_key, name='channel_public_key'),
]
