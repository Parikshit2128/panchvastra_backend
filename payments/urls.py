from django.urls import path
from .views import checkout_payment, verify_payment_api, webhook

urlpatterns = [
    path("checkout_payment/", checkout_payment, name="checkout_payment"),
    path("verify_payment_api/", verify_payment_api, name="verify_payment_api"),
    path("webhook/", webhook, name="webhook"),
]