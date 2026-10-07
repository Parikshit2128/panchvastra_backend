from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view
)

from pv_app.api.serializer.sz_support import (
    CreateSupportQuerySerializer,
    UpdateSupportQuerySerializer
)


submit_support_query_schema = extend_schema_view(

    post=extend_schema(
        tags=["Help Desk"],
        summary="Submit a Help Desk query",
        description=(
            "Public — no token required. Stores the query as OPEN. If a valid "
            "token is sent anyway the query is linked to that user; an "
            "invalid or expired token is ignored rather than rejected, so a "
            "stale login never blocks someone from asking for help.\n\n"
            "category must be one of: ORDER_SUPPORT, SIZE_PRODUCT, "
            "COLLABORATION, PAYMENT, WEBSITE, OTHER. name is capped at 100 "
            "characters and message at 2000. Limited to 5 submissions a "
            "minute per IP; a 429 means wait and retry."
        ),
        request=CreateSupportQuerySerializer
    )
)


support_queries_admin_schema = extend_schema_view(

    get=extend_schema(
        tags=["Help Desk"],
        summary="List or fetch Help Desk queries",
        description=(
            "Admin only. With id returns that one query. Otherwise a "
            "paginated list, un-resolved queries first then newest first."
        ),
        parameters=[
            OpenApiParameter(name="id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="page", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="page_size", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name="category", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                description="ORDER_SUPPORT | SIZE_PRODUCT | COLLABORATION | PAYMENT | WEBSITE | OTHER"
            ),
            OpenApiParameter(
                name="status", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                description="OPEN | IN_PROGRESS | RESOLVED"
            ),
            OpenApiParameter(
                name="search_parameter", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                description="Matches the sender's name or email"
            )
        ]
    ),

    put=extend_schema(
        tags=["Help Desk"],
        summary="Change a query's status",
        description="Admin only. Returns the updated query.",
        request=UpdateSupportQuerySerializer
    )
)
