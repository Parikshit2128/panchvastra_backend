from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiTypes
)

from pv_app.api.serializer.sz_user_panel import CreateCategorySerializer, UpdateCategorySerializer


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
        description="""
        Fetch products with filters, sorting, pagination, and product details.

        Supported Filters:
        - category_id
        - sub_category_id
        - size
        - min_price
        - max_price
        - search

        Supported Sorting:
        - latest
        - oldest
        - price_low_to_high
        - price_high_to_low

        Examples:

        /products?page=1&page_size=20

        /products?id=1

        /products?category_id=1

        /products?sub_category_id=2

        /products?size=M

        /products?min_price=500&max_price=1500

        /products?search=oversized

        /products?sort_by=price_low_to_high

        /products?category_id=1&size=L&min_price=500&max_price=1500&sort_by=price_low_to_high
        """,
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
        ],
    )
)