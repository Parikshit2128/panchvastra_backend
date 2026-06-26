from rest_framework import serializers


class CreateCategorySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    image_url = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)


class UpdateCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    image_url = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)



class AddToCartSerializer(serializers.Serializer):
    variant_size_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=False, default=1, min_value=1)

class UpdateCartSerializer(serializers.Serializer):
    cart_item_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True, min_value=1)



class CouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=100)
    discount_type = serializers.ChoiceField(
        choices=["PERCENTAGE", "FLAT"]
    )
    discount_value = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    maximum_discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    minimum_order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0
    )
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    max_usage = serializers.IntegerField(
        required=False,
        allow_null=True
    )
    max_usage_per_user = serializers.IntegerField(
        required=False,
        default=1
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )
    is_first_order_only = serializers.BooleanField(
        required=False,
        default=False
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True
    )


class UpdateCouponSerializer(CouponSerializer):
    id = serializers.IntegerField()
    is_active = serializers.BooleanField(required=False, default=True)