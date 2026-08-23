from rest_framework.decorators import api_view
from rest_framework.response import Response

from helpers.middleware import user_authentication_required
from helpers.utils import generic_response_handler

from .serializers import CheckoutOrderSerializer, VerifyPaymentSerializer
from .business_logic import create_checkout_payment, razorpay_webhook_handler, verify_payment
from .swagger import checkout_payment_schema


@checkout_payment_schema
@user_authentication_required(role_required=2)
@api_view(["POST"])
@generic_response_handler
def checkout_payment(request):
    serializer = CheckoutOrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return create_checkout_payment(
        serializer.validated_data,
        user_id=request.user_id
    )


@user_authentication_required(role_required=2)
@api_view(["POST"])
@generic_response_handler
def verify_payment_api(request):
    serializer = VerifyPaymentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return verify_payment(serializer.validated_data, user_id=request.user_id)


@api_view(["POST"])
def webhook(request):
    return razorpay_webhook_handler(request)