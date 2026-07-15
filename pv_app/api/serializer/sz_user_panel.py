from rest_framework import serializers


class CreateCategorySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)
    is_active = serializers.BooleanField(required=False, default=True)


class UpdateCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)
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



class ProductVariantSizeSerializer(serializers.Serializer):
    id = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    size = serializers.CharField(max_length=20)

    stock_quantity = serializers.IntegerField(
        min_value=0
    )


class ProductVariantSerializer(serializers.Serializer):
    id = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    sku = serializers.CharField(max_length=100)

    color = serializers.CharField(max_length=100)

    mrp = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0
    )

    selling_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0
    )

    cost_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )

    is_default = serializers.BooleanField(default=False)

    sizes = ProductVariantSizeSerializer(
        many=True
    )

    def validate(self, attrs):
        if attrs["selling_price"] > attrs["mrp"]:
            raise serializers.ValidationError(
                {
                    "selling_price": "Selling price cannot be greater than MRP."
                }
            )

        return attrs
    

class CreateProductSerializer(serializers.Serializer):

    category_id = serializers.IntegerField()

    sub_category_id = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    name = serializers.CharField(max_length=255)

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    fabric = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    gsm = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    is_featured = serializers.BooleanField(default=False)

    is_new_arrival = serializers.BooleanField(default=False)

    is_active = serializers.BooleanField(default=True)

    key_highlights = serializers.JSONField(
        required=False,
        default=dict
    )

    tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

    variants = ProductVariantSerializer(
        many=True
    )

    def validate(self, attrs):

        variants = attrs["variants"]

        if len(variants) == 0:
            raise serializers.ValidationError(
                {
                    "variants": "At least one variant is required."
                }
            )

        default_count = sum(
            variant.get("is_default", False)
            for variant in variants
        )

        if default_count != 1:
            raise serializers.ValidationError(
                {
                    "variants": "Exactly one default variant is required."
                }
            )

        return attrs
    


class UpdateProductSerializer(CreateProductSerializer):

    id = serializers.IntegerField()

    