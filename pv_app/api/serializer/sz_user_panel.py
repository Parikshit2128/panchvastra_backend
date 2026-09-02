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


class CreateSubCategorySerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    is_active = serializers.BooleanField(required=False, default=True)


class UpdateSubCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    category_id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=255, required=False)
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
        decimal_places=2,
        min_value=0
    )
    maximum_discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0
    )
    minimum_order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0,
        min_value=0
    )
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    max_usage = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1
    )
    max_usage_per_user = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1
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

    def validate(self, attrs):
        if attrs["discount_type"] == "PERCENTAGE" and attrs["discount_value"] > 100:
            raise serializers.ValidationError(
                {"discount_value": "A percentage discount cannot exceed 100."}
            )

        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be before the start date."}
            )

        return attrs


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
    is_active = serializers.BooleanField(required=False, default=True)


class ProductVariantSerializer(serializers.Serializer):
    id = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    sku = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True
    )

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

    is_default = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)

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
        many=True, required=True, allow_empty=False
    )

    


class CreateAddressSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    mobile = serializers.CharField(max_length=20)
    address_line_1 = serializers.CharField(max_length=500)
    address_line_2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    landmark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100, required=False, default="India")
    pincode = serializers.CharField(max_length=10)
    address_type = serializers.ChoiceField(choices=["Home", "Work", "Other"], required=False, default="Home")
    is_default = serializers.BooleanField(required=False, default=False)


class UpdateAddressSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField(max_length=255, required=False)
    mobile = serializers.CharField(max_length=20, required=False)
    address_line_1 = serializers.CharField(max_length=500, required=False)
    address_line_2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    landmark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(max_length=100, required=False)
    state = serializers.CharField(max_length=100, required=False)
    country = serializers.CharField(max_length=100, required=False)
    pincode = serializers.CharField(max_length=10, required=False)
    address_type = serializers.ChoiceField(choices=["Home", "Work", "Other"], required=False)
    is_default = serializers.BooleanField(required=False)


class NotifyMeSerializer(serializers.Serializer):
    variant_size_id = serializers.IntegerField(required=True)


class ProductImageUploadSerializer(serializers.Serializer):
    """Documents the multipart/form-data shape for Create/Update Product
    when attaching variant image files — a separate, honest schema from
    CreateProductSerializer/UpdateProductSerializer because multipart can't
    express a nested variants[].images list of files the way JSON can.
    """

    data = serializers.CharField(
        help_text=(
            "The full product payload as a JSON string, same shape as the "
            "application/json request body (CreateProductSerializer for "
            "POST, UpdateProductSerializer for PUT). variants[].images is "
            "not part of this JSON — attach files separately below."
        )
    )

    variant_0_images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        help_text=(
            "Image files for variants[0] in 'data'. Matches each variant's "
            "zero-based position in the 'variants' array (works for "
            "brand-new variants too — they don't need an id yet). No "
            "limit on images per variant."
        )
    )

    variant_1_images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        help_text="Image files for variants[1] in 'data'. Same pattern as variant_0_images."
    )

    variant_2_images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        help_text=(
            "Image files for variants[2] in 'data'. Same pattern as "
            "variant_0_images. For a 4th+ variant, this Swagger form runs "
            "out of fields — use 'Copy as cURL' from a filled-in request "
            "here and add more variant_<index>_images fields by hand."
        )
    )


class UpdateProductSerializer(CreateProductSerializer):

    id = serializers.IntegerField()

    # Unlike create, an update may legitimately touch nothing about variants
    # (e.g. just renaming the product), so this loosens the base class's
    # required=True back down for updates only.
    variants = ProductVariantSerializer(
        many=True, required=False, default=list
    )

    delete_tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

    delete_variant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

    delete_size_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

    delete_variant_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

