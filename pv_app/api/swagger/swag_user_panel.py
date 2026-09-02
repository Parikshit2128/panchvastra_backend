from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiTypes
)

from pv_app.api.serializer.sz_user_panel import AddToCartSerializer, CouponSerializer, CreateAddressSerializer, CreateCategorySerializer, CreateProductSerializer, NotifyMeSerializer, ProductImageUploadSerializer, UpdateAddressSerializer, UpdateCartSerializer, UpdateCategorySerializer, UpdateCouponSerializer, UpdateProductSerializer


categories_management_schema = extend_schema_view(
    get=extend_schema(
        tags=["Categories"],
        description="Get category details. Fetch a specific category using id or all categories.",
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False
            ),
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False
            ),
            OpenApiParameter(
                name="search_parameter",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False
            )
        ],
    ),

    post=extend_schema(
        tags=["Categories"],
        description="Create a new category.",
        request=CreateCategorySerializer,
    ),

    put=extend_schema(
        tags=["Categories"],
        description="Update an existing category.",
        request=UpdateCategorySerializer,
    ),

    delete=extend_schema(
        tags=["Categories"],
        description="Soft delete a category.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True
            )
        ],
    ),
)



products_management_schema = extend_schema_view(

    get=extend_schema(
        tags=["Products"],
        summary="Get Product(s)",
        description="Fetch product listing or product details.",
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Page number. Default: 1"
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Records per page. Default: 20"
            ),
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Fetch a specific product by ID"
            ),
            OpenApiParameter(
                name="category_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by category ID"
            ),
            OpenApiParameter(
                name="sub_category_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by sub-category ID"
            ),
            OpenApiParameter(
                name="size",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by size (S, M, L, XL)"
            ),
            OpenApiParameter(
                name="min_price",
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Minimum selling price"
            ),
            OpenApiParameter(
                name="max_price",
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum selling price"
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Search by product name, description, fabric or color"
            ),
            OpenApiParameter(
                name="sort_by",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="""
                Sorting options:
                - latest
                - oldest
                - price_low_to_high
                - price_high_to_low
                """
            ),
            OpenApiParameter(
                name="tag",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by tag"
            ),
        ],
    ),

    post=extend_schema(
        tags=["Products"],
        summary="Create Product",
        description="""
        Create a new product with variants, sizes and images.

        Images belong to a variant, not the product directly (they're stored
        in product_variant_images, keyed by variant_id) — this is the same
        relationship the GET response already exposes as variants[].images.

        Two ways to submit this request:

        1) application/json (no image files) — body is the product object
           exactly as before; variants[].images is simply omitted.

        2) multipart/form-data (to attach image files) — because multipart
           has no way to express a nested variants[].images list of files,
           send the exact same product JSON as a string in a 'data' field,
           and attach each variant's files separately as
           variant_<index>_images, where <index> is that variant's
           zero-based position in the 'variants' array inside 'data'
           (works for brand-new variants too, since they don't have an id
           yet). Multiple files can be attached under the same
           variant_<index>_images field name. There is no limit on the
           number of images per variant.

        display_order is assigned automatically in submission order,
        starting at 1 for a new product/variant.
        """,
        request={
            "application/json": CreateProductSerializer,
            "multipart/form-data": ProductImageUploadSerializer,
        },
    ),

    put=extend_schema(
        tags=["Products"],
        summary="Update Product",
        description="""
        Update an existing product.

        Business Rules:
        - If id exists in child records → Update.
        - If id is missing → Create new child.
        - delete_variant_ids → Soft delete variants (and their sizes/images).
        - delete_size_ids → Soft delete variant sizes.
        - delete_variant_image_ids → Soft delete specific variant images by
          their image id. Images NOT listed here are left untouched —
          sending new images or other product fields never removes existing
          images on its own.

        Image submission uses the same contract as CREATE: send
        multipart/form-data with the product/variant JSON as a string in a
        'data' field, plus variant_<index>_images file field(s) per variant
        (index = that variant's position in the 'variants' array inside
        'data', whether the variant is being updated or newly added in this
        same request). New images are appended after the current highest
        display_order for that variant, so existing ordering is preserved.
        A plain application/json body (no files) continues to work exactly
        as before.
        """,
        request={
            "application/json": UpdateProductSerializer,
            "multipart/form-data": ProductImageUploadSerializer,
        },
    ),

    delete=extend_schema(
        tags=["Products"],
        summary="Delete Product",
        description="Soft delete a product.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Unique ID of the product to delete."

    ),
        ],
    ),
)


cart_management_schema = extend_schema_view(
    post=extend_schema(
        tags=["Cart"],
        summary="Add item to cart",
        description="Adds a specific variant size product to the user's cart. If it already exists, increments quantity.",
        request=AddToCartSerializer,
    ),
    get=extend_schema(
        tags=["Cart"],
        summary="Retrieve user cart",
        description="Fetches all active items inside the user's cart alongside full layout metadata and live checkout summary calculations.",
    ),
    put=extend_schema(
        tags=["Cart"],
        summary="Update cart item quantity",
        description="Directly overrides and updates the structural quantity threshold of a specific active item line inside the cart.",
        request=UpdateCartSerializer,
    ),
    delete=extend_schema(
        tags=["Cart"],
        summary="Remove item from cart",
        description="Performs a safe logical deletion to drop an item line cleanly from the active shopping cart layout.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="The unique ID of the cart item (`cart_item_id`) to be removed."
            ),
        ],
    ),
)




coupon_management_schema = extend_schema_view(

    post=extend_schema(
        tags=["Coupon Management"],
        summary="Create coupon",
        description=(
            "Creates a new coupon with discount configuration, "
            "usage limits, validity period, and eligibility rules."
        ),
        request=CouponSerializer,
    ),

    get=extend_schema(
        tags=["Coupon Management"],
        summary="Retrieve coupons",
        description=(
            "Returns all active coupons or fetches a specific coupon "
            "using either its unique ID or coupon code."
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Unique coupon ID."
            ),
            OpenApiParameter(
                name="code",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Coupon code (case-insensitive). Example: SAVE100"
            ),
        ],
    ),

    put=extend_schema(
        tags=["Coupon Management"],
        summary="Update coupon",
        description=(
            "Updates an existing coupon including discount values, "
            "usage limits, validity dates, status, and eligibility rules."
        ),
        request=UpdateCouponSerializer,
    ),

    delete=extend_schema(
        tags=["Coupon Management"],
        summary="Delete coupon",
        description=(
            "Performs a soft delete by marking the coupon as inactive "
            "and deleted."
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Unique ID of the coupon to delete."
            ),
        ],
    ),
)




address_management_schema = extend_schema_view(

    post=extend_schema(
        tags=["Address Management"],
        summary="Create address",
        description="Adds a new address to the authenticated user's address book. The first address created is automatically set as default.",
        request=CreateAddressSerializer,
    ),

    get=extend_schema(
        tags=["Address Management"],
        summary="Retrieve addresses",
        description="Returns all saved addresses for the authenticated user, or fetches a specific address by id.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Unique ID of the address to fetch."
            ),
        ],
    ),

    put=extend_schema(
        tags=["Address Management"],
        summary="Update address",
        description="Updates an existing address belonging to the authenticated user. Setting is_default to true unsets any other default address.",
        request=UpdateAddressSerializer,
    ),

    delete=extend_schema(
        tags=["Address Management"],
        summary="Delete address",
        description="Soft deletes an address. If the deleted address was the default, the most recently created remaining address becomes the new default.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Unique ID of the address to delete."
            ),
        ],
    ),
)




notify_me_schema = extend_schema_view(

    post=extend_schema(
        tags=["Notify Me"],
        summary="Subscribe to restock notification",
        description="Registers an email to be notified when a specific out-of-stock product size becomes available again.",
        request=NotifyMeSerializer,
    ),

    get=extend_schema(
        tags=["Notify Me"],
        summary="List pending notify-me requests",
        description="Returns pending (not yet notified) restock subscriptions, optionally filtered by variant_size_id.",
        parameters=[
            OpenApiParameter(
                name="variant_size_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by a specific product variant size ID."
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False
            ),
        ],
    ),

    delete=extend_schema(
        tags=["Notify Me"],
        summary="Cancel a notify-me subscription",
        description="Cancels a pending restock notification subscription. Requires the subscription id and the matching email.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Unique ID of the notify-me request to cancel."
            ),
            OpenApiParameter(
                name="email",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Email used when subscribing, used to verify ownership."
            ),
        ],
    ),
)



orders_schema = extend_schema_view(

    get=extend_schema(
        tags=["Order History"],
        summary="Retrieve orders",
        description=(
            "Returns all orders for the authenticated user or fetches a specific order "
            "using its unique ID."
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False
            ),
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False
            ),
        ],
    ),
)