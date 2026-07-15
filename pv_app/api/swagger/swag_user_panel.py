from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiTypes
)

from pv_app.api.serializer.sz_user_panel import AddToCartSerializer, CouponSerializer, CreateCategorySerializer, UpdateCartSerializer, UpdateCategorySerializer, UpdateCouponSerializer


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
                description="Filter by size. Example: S, M, L, XL"
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
                description="Search by product name, description, fabric, or color"
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
    )
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