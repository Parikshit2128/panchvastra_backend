from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view
)

from pv_app.api.serializer.sz_custom import (
    CreateCustomRequestSerializer,
    CustomOptionSerializer,
    UpdateCustomOptionSerializer,
    UpdateCustomRequestSerializer
)


custom_options_schema = extend_schema_view(

    get=extend_schema(
        tags=["Custom Piece"],
        summary="Options for the Build Your Piece page",
        description=(
            "Public. Returns garments, colours, sizes and print types in one "
            "call, each sorted by display_order. Each garment carries "
            "colour_ids: the only colours it can be ordered in (this is how "
            "\"Hoodie is available only in Black\" is expressed). The public "
            "view hides inactive options and any garment left with no active "
            "colour. An admin token with include_inactive=true also gets "
            "inactive options and an is_active flag on each."
        ),
        parameters=[
            OpenApiParameter(
                name="include_inactive", type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY, required=False,
                description="Admin only"
            )
        ]
    ),

    post=extend_schema(
        tags=["Custom Piece"],
        summary="Create an option (admin)",
        description=(
            "option_type is GARMENT, COLOUR, SIZE or PRINT_TYPE. A COLOUR "
            "needs hex_code (#RRGGBB). A GARMENT needs colour_ids (repeat the "
            "field per id in multipart). Only GARMENT and PRINT_TYPE take an "
            "image. Omit display_order to place it last within its type."
        ),
        request={
            "multipart/form-data": CustomOptionSerializer,
            "application/json": CustomOptionSerializer
        }
    ),

    put=extend_schema(
        tags=["Custom Piece"],
        summary="Edit an option (admin)",
        description=(
            "Send only what changes. option_type cannot change. colour_ids "
            "replaces the garment's whole colour list. A new image replaces "
            "the old one."
        ),
        request={
            "multipart/form-data": UpdateCustomOptionSerializer,
            "application/json": UpdateCustomOptionSerializer
        }
    ),

    delete=extend_schema(
        tags=["Custom Piece"],
        summary="Delete an option (admin)",
        description="Soft delete. Existing requests keep the option's name.",
        parameters=[
            OpenApiParameter(
                name="id", type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY, required=True
            )
        ]
    )
)


custom_requests_schema = extend_schema_view(

    get=extend_schema(
        tags=["Custom Piece"],
        summary="List or fetch custom requests",
        description=(
            "A customer token returns that customer's own requests; an admin "
            "token returns all. With id, returns one request plus its "
            "history. Customers see status changes only; admins also see "
            "notes and who made each change."
        ),
        parameters=[
            OpenApiParameter(name="id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="page", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="page_size", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="status", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                description="NEW | IN_REVIEW | APPROVED | IN_PRODUCTION | SHIPPED | DELIVERED | CANCELLED"
            ),
            OpenApiParameter(
                name="search_parameter", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                description="Admin only. Request number, name or phone."
            )
        ]
    ),

    post=extend_schema(
        tags=["Custom Piece"],
        summary="Submit a custom piece (Create my piece)",
        description=(
            "Login required. multipart/form-data. design_file is PNG, JPG or "
            "PDF up to 10 MB, checked by content. Send design_file, "
            "design_description (max 300), or both; at least one is "
            "required. The garment must come in the chosen colour. "
            "Limited to 10 submissions a minute."
        ),
        request={"multipart/form-data": CreateCustomRequestSerializer}
    ),

    put=extend_schema(
        tags=["Custom Piece"],
        summary="Update a request's status / add a note (admin)",
        description="Send status, note, or both. Returns the full request with history.",
        request=UpdateCustomRequestSerializer
    )
)
