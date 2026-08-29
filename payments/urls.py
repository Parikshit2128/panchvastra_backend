from django.urls import path
from .views import checkout_payment, cod_order, verify_payment_api, webhook

urlpatterns = [
    path("checkout_payment/", checkout_payment, name="checkout_payment"),
    path("cod_order/", cod_order, name="cod_order"),
    path("verify_payment_api/", verify_payment_api, name="verify_payment_api"),
    path("webhook/", webhook, name="webhook"),
]