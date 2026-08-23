from rest_framework import serializers


class CheckoutOrderSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    coupon_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()