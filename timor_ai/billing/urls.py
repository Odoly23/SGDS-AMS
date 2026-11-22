from django.urls import path

from . import views

urlpatterns = [
    path("api/wallet/", views.WalletView.as_view(), name="api-wallet"),
    path("api/redeem/", views.RedeemView.as_view(), name="api-redeem"),
]
