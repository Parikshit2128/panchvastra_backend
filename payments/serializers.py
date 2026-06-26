from rest_framework import serializers


class CheckoutOrderSerializer(serializers.Serializer):
    # user_id = serializers.IntegerField()
    customer_name = serializers.CharField()
    customer_email = serializers.EmailField(required=False, allow_null=True)
    customer_mobile = serializers.CharField()

    address_line_1 = serializers.CharField()
    address_line_2 = serializers.CharField(required=False, allow_blank=True)
    landmark = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField()
    state = serializers.CharField()
    pincode = serializers.CharField()

    coupon_code = serializers.CharField(required=False, allow_blank=True)

    items = serializers.ListField()