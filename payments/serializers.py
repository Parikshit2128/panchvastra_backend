from rest_framework import serializers


class CheckoutOrderSerializer(serializers.Serializer):
    address_id = serializers.IntegerField(min_value=1)
    coupon_code = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=64)
    razorpay_payment_id = serializers.CharField(max_length=64)
    razorpay_signature = serializers.CharField(max_length=128)