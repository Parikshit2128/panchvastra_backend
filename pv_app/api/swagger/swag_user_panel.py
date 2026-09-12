from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiTypes
)

from pv_app.api.serializer.sz_user_panel import AddToCartSerializer, CouponSerializer, CreateAddressSerializer, CreateAuthCarouselImageSerializer, CreateCategorySerializer, CreateProductSerializer, CreateSubCategorySerializer, NotifyMeAdminListResponseSerializer, NotifyMeSerializer, ProductImageUploadSerializer, UpdateAddressSerializer, UpdateAuthCarouselImageSerializer, UpdateCartSerializer, UpdateCategorySerializer, UpdateCouponSerializer, UpdateOrderStatusSerializer, UpdateProductSerializer, UpdateSubCategorySerializer


auth_carousel_schema = extend_schema_view(
    get=extend_schema(
        tags=["Auth Carousel"],
        description=(
            "Get carousel/banner images for the Login and Signup pages, "
            "ordered by display_order. Public and no token required — in "
            "that case only active images are returned. An admin token "
            "additionally returns inactive images, so the admin panel can "
            "find and re-activate one. Pass 'id' to fetch a single image."
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Fetch a specific carousel image by ID."
            ),
        ],
    ),

    post=extend_schema(
        tags=["Auth Carousel"],
        description=(
            "Upload a new carousel image. Admin only. If display_order is "
            "omitted, it's assigned automatically as the current highest "
            "display_order + 1."
        ),
        request=CreateAuthCarouselImageSerializer,
    ),

    put=extend_schema(
        tags=["Auth Carousel"],
        description=(
            "Update a carousel image — replace the image file, change its "
            "display_order, or toggle is_active. Admin only. Send only "
            "the fields you're changing."
        ),
        request=UpdateAuthCarouselImageSerializer,
    ),

    delete=extend_schema(
        tags=["Auth Carousel"],
        description="Soft delete a carousel image. Admin only.",
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


categories_management_schema = extend_schema_view(
    get=extend_schema(
        tags=["Categories"],
        description=(
            "Get category details. Fetch a specific category using id or "
            "all categories. Results are returned in display_order ASC "
            "(ties broken by newest first), which is the order the "
            "storefront and admin list should render — no client-side "
            "sorting needed."
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
                name="search_parameter",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False
            )
        ],
    ),

    post=extend_schema(
        tags=["Categories"],
        description=(
            "Create a new category. display_order is optional — omit it and "
            "the category is appended last (current highest + 1). Send it to "
            "place the category at a specific position."
        ),
        request=CreateCategorySerializer,
    ),

    put=extend_schema(
        tags=["Categories"],
        description=(
            "Update an existing category. Send display_order to reposition "
            "it; omit the field and the current position is left untouched. "
            "Positions are not required to be unique or contiguous — GET "
            "simply sorts by display_order ASC."
        ),
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


sub_categories_management_schema = extend_schema_view(
    get=extend_schema(
        tags=["Sub Categories"],
        description=(
            "Get sub category details. Fetch a specific sub category using "
            "id, all sub categories under a category, or all sub "
            "categories. Results are returned in display_order ASC (ties "
            "broken by newest first). Ordering is scoped to the parent "
            "category, so combine with category_id to get one category's "
            "sub categories in their intended order."
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
                name="category_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by parent category ID"
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
        tags=["Sub Categories"],
        description=(
            "Create a new sub category under a category. display_order is "
            "optional — omit it and the sub category is appended last "
            "WITHIN ITS PARENT CATEGORY (that category's current highest + "
            "1), so position 1 under 'Men' is independent of position 1 "
            "under 'Women'."
        ),
        request=CreateSubCategorySerializer,
    ),

    put=extend_schema(
        tags=["Sub Categories"],
        description=(
            "Update an existing sub category. Send display_order to "
            "reposition it within its parent category; omit the field and "
            "the current position is left untouched. Note that moving a sub "
            "category to a different category_id does NOT renumber its "
            "display_order — send both fields together if the position "
            "should change too."
        ),
        request=UpdateSubCategorySerializer,
    ),

    delete=extend_schema(
        tags=["Sub Categories"],
        description="Soft delete a sub category.",
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
        starting at 1 for a new product/variant, UNLESS a same-indexed
        variant_<index>_image_orders field is sent — see UPDATE's
        documentation below for the full rules; they apply identically
        here since new-image upload uses one shared code path for both.

        KEY HIGHLIGHTS — key_highlights is an ordered ARRAY of
        {label, value} objects (never a raw JSON object):

            "key_highlights": [
              {"label": "Product Category", "value": "Topwear"},
              {"label": "Fit", "value": "Regular Fit"},
              {"label": "Fabric", "value": "Breathable Fabric"}
            ]

        Labels are free-form — they are NOT a fixed list, so a hoodie can
        send {"label": "Hood Type", ...} and a cap {"label": "Closure
        Type", ...}. Array order is preserved end to end and is the order
        the customer product page renders, so the admin's sequence is
        what ships; nothing is sorted server-side. The field is optional
        and [] is valid. Rejected with 400: anything that isn't an array
        (a bare {} or string), entries that aren't objects, a missing or
        empty/whitespace-only label or value, and two entries sharing a
        label (compared case-insensitively).

        In multipart/form-data, key_highlights travels inside the 'data'
        JSON string like every other product field — it is NOT a separate
        form part.
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

        DRAG-AND-DROP IMAGE ORDERING (both existing and newly uploaded
        images, as one interleaved list):

        1) Reordering EXISTING images — variant_image_orders, inside the
           'data' JSON (NOT a separate multipart field):
             "variant_image_orders": [
               {"id": 91, "display_order": 2},
               {"id": 88, "display_order": 3}
             ]
           Each id must be an existing product_variant_images row that
           belongs to THIS product (validated server-side against the
           actual product -> variant -> image relationship — a foreign
           image id returns 400) — its display_order changes, nothing
           else about it does, and its id never changes. An existing
           image NOT listed here keeps its current display_order
           untouched — this never auto-renumbers the rest of the variant.

        2) Ordering NEWLY UPLOADED images — a same-indexed
           variant_<index>_image_orders multipart field, positional against
           variant_<index>_images (the Nth order value is the Nth file's
           display_order, regardless of filename):
             variant_0_images: newA.jpg, newB.jpg
             variant_0_image_orders: 1, 4
           newA.jpg -> display_order 1, newB.jpg -> display_order 4. This
           is OPTIONAL and per-variant: a variant with uploaded images but
           no *_image_orders field keeps the old auto-append behavior
           (appended after the current max display_order); a variant WITH
           it uses those exact values instead — new images are then never
           auto-appended for that variant, so its *_image_orders length
           must equal its *_images file count (400 otherwise).

        3) Interleaving both in one request — combine 1) and 2): e.g. move
           existing image 91 to position 2 via variant_image_orders while
           uploading a new image at position 1 via variant_0_image_orders
           — both apply together against the same final per-variant
           sequence.

        Validation (400 on any failure, nothing is partially applied —
        this validates everything before writing anything):
        - Every variant_image_orders id must belong to this product.
        - display_order must be a positive integer (0, negative, decimal,
          non-numeric all rejected).
        - The FINAL image set of each affected variant — existing images
          that survive deletion (with any requested reorder applied) plus
          any explicitly-ordered new images — must not contain a duplicate
          display_order. Checked per variant, never across variants.
        - variant_<index>_image_orders' length must equal
          variant_<index>_images' file count.

        Backward compatible: omit variant_image_orders and every
        variant_<index>_image_orders entirely and this endpoint behaves
        exactly as it did before — no new field is required.

        KEY HIGHLIGHTS — same array-of-{label, value} contract, ordering
        and validation as CREATE (see above). Sending key_highlights
        REPLACES the product's current highlights wholesale with the list
        given, so the admin panel should always submit the complete final
        list — adding, editing, removing and reordering are all expressed
        by simply sending the list as it should end up. Omitting the field
        leaves whatever is stored untouched is NOT the behavior: like the
        other scalar product fields on this endpoint, an omitted
        key_highlights falls back to its default ([]) and clears the
        stored value, so always send the full list you want persisted.

        Reading back: GET product detail always returns key_highlights in
        the {label, value} array shape, including for products saved
        before this contract existed (older rows held either {} or a plain
        array of strings; those are converted on read, never rewritten in
        place, and a legacy bare string comes back as {"label": "",
        "value": "<original text>"}).
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
        summary="Admin: list notify-me requests",
        description=(
            "Admin only (403 for a non-admin token) — returns the full "
            "restock-notification waitlist across all customers, resolved "
            "server-side to product/variant/size/email in one query. "
            "Optionally filtered to one variant_size_id. Includes both "
            "pending and already-notified requests — see is_notified."
        ),
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
                required=False,
                description="Default: 1"
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Default: 20"
            ),
        ],
        responses={200: NotifyMeAdminListResponseSerializer},
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
            "Returns orders for the authenticated user, or fetches a specific "
            "order by id. An admin token returns orders across every "
            "customer instead of just their own, and can open any order's "
            "detail regardless of who placed it."
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
                name="order_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="'current' (PLACED/CONFIRMED/PACKED/SHIPPED/OUT_FOR_DELIVERY) or 'history' (DELIVERED/CANCELLED)."
            ),
            OpenApiParameter(
                name="search_parameter",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Admin only — search by order number, customer name, or email."
            ),
        ],
    ),

    put=extend_schema(
        tags=["Order History"],
        summary="Update order status",
        description=(
            "Update an order's status (and optionally tracking_id / "
            "courier_name). Admin only. shipped_at / delivered_at / "
            "cancelled_at are stamped automatically the first time that "
            "status is reached."
        ),
        request=UpdateOrderStatusSerializer,
    ),
)