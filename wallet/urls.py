from django.urls import path

from . import views

app_name = "wallet"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("buy/<str:code>/payment/", views.buy_payment, name="buy_payment"),
    path("sell/confirm/", views.sell_confirm, name="sell_confirm"),
    path("transfer/confirm/", views.transfer_confirm, name="transfer_confirm"),
    path("transfer/lookup/", views.receiver_lookup, name="receiver_lookup"),
    path("coin-image/", views.coin_image_url, name="coin_image_url"),
    path("history/", views.history, name="history"),
]