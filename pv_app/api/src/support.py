import jwt

from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import ScopedRateThrottle

from helpers.middleware import user_authentication_required
from helpers.utils import decode_jwt_token, generic_response_handler
from pv_app.api.business_logic.bl_support import (
    create_support_query,
    get_support_queries,
    update_support_query_status
)
from pv_app.api.serializer.sz_support import (
    CreateSupportQuerySerializer,
    UpdateSupportQuerySerializer
)
from pv_app.api.swagger.swag_support import (
    submit_support_query_schema,
    support_queries_admin_schema
)


def _optional_user_id(request):
    """The caller's user id if they sent a usable token, otherwise None.

    Deliberately lenient, unlike user_authentication_required: this endpoint
    is public, so a token that has expired must not turn "I need help" into a
    401. A bad token just means the query is stored as anonymous.
    """

    header = request.headers.get("Authorization")

    if not header:
        return None

    try:
        return decode_jwt_token(header).get("user_id")
    except (ValueError, jwt.InvalidTokenError):
        return None


@submit_support_query_schema
@api_view(["POST"])
@throttle_classes([ScopedRateThrottle])
@generic_response_handler
def submit_support_query(request):
    serializer = CreateSupportQuerySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return create_support_query(
        serializer.validated_data,
        user_id=_optional_user_id(request)
    )


submit_support_query.cls.throttle_scope = "support_query"


@support_queries_admin_schema
@user_authentication_required(role_required=[1])
@api_view(["GET", "PUT"])
@generic_response_handler
def support_queries_management(request):

    if request.method == "PUT":
        serializer = UpdateSupportQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return update_support_query_status(serializer.validated_data)

    return get_support_queries(
        query_id=request.GET.get("id"),
        page=request.GET.get("page", 1),
        page_size=request.GET.get("page_size", 10),
        category=request.GET.get("category"),
        query_status=request.GET.get("status"),
        search=request.GET.get("search_parameter")
    )
