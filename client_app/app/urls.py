from django.urls import path

from .views.assets import AssetExposeView, AssetSetupView, AssetsListView, AssetUseView
from .views.config import ConfigPageView, IdentitySetView
from .views.issuers import IssuerDetailView, IssuersListView
from .views.wallets import WalletDetailView, WalletsListView

# Each URL is the canonical home for its resource. GET shows the page (and
# any inline forms); POST processes the form and redirects back. No JSON APIs.
urlpatterns = [
    # Assets
    path('', AssetsListView.as_view(), name='assets_page'),
    path('assets/setup/', AssetSetupView.as_view(), name='asset_setup'),
    path('assets/<int:pk>/expose/', AssetExposeView.as_view(), name='asset_expose'),
    path('assets/use/', AssetUseView.as_view(), name='asset_use'),

    # Wallets
    path('wallets/', WalletsListView.as_view(), name='wallets'),
    path('wallets/<int:pk>/', WalletDetailView.as_view(), name='wallet_detail'),

    # Issuers
    path('issuers/', IssuersListView.as_view(), name='issuers'),
    path('issuers/<int:pk>/', IssuerDetailView.as_view(), name='issuer_detail'),

    # Config + identity
    path('config/', ConfigPageView.as_view(), name='config'),
    path('identity/set/', IdentitySetView.as_view(), name='identity_set'),
]
