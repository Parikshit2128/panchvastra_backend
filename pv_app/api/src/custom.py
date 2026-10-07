from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.throttling import ScopedRateThrottle

from helpers.middleware import user_authentication_required
from helpers.utils import generic_response_handler
from pv_app.api.business_logic.bl_custom import (
    create_custom_option,
    create_custom_request,
    delete_custom_option,
    get_custom_options,
    get_custom_requests,
    update_custom_option,
    update_custom_request
)
from pv_app.api.serializer.sz_custom import (
    CreateCustomRequestSerializer,
    CustomOptionSerializer,
    UpdateCustomOptionSerializer,
    UpdateCustomRequestSerializer
)
from pv_app.api.swagger.swag_custom import (
    custom_options_schema,
    custom_requests_schema
)


ADMIN_ONLY = (
    {"message": "You are not authorized to perform this action.", "data": {}},
    status.HTTP_403_FORBIDDEN
)


class SubmitOnlyThrottle(ScopedRateThrottle):
    """Limits POST only. A plain ScopedRateThrottle on this view would also
    count the customer's and admin's GETs, and paging through the admin list
    would start returning 429."""

    def allow_request(self, request, view):
        if request.method != "POST":
            return True
        return super().allow_request(request, view)


@custom_options_schema
@user_authentication_required(role_required=[1, 2], public_methods=["GET"])
@api_view(["GET", "POST", "PUT", "DELETE"])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@generic_response_handler
def custom_options(request):

    is_admin = request.role_id == 1

    if request.method == "GET":
        include_inactive = (
            is_admin
            and str(request.GET.get("include_inactive", "")).lower() == "true"
        )
        return get_custom_options(include_inactive=include_inactive)

    if not is_admin:
        return ADMIN_ONLY

    if request.method == "POST":
        serializer = CustomOptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return create_custom_option(serializer.validated_data, user_id=request.user_id)

    if request.method == "PUT":
        serializer = UpdateCustomOptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return update_custom_option(dict(serializer.validated_data), user_id=request.user_id)

    option_id = request.GET.get("id")

    if not option_id:
        return {"message": "id is required.", "data": {}}, status.HTTP_400_BAD_REQUEST

    return delete_custom_option(option_id, user_id=request.user_id)


@custom_requests_schema
@user_authentication_required(role_required=[1, 2])
@api_view(["GET", "POST", "PUT"])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@throttle_classes([SubmitOnlyThrottle])
@generic_response_handler
def custom_requests(request):

    is_admin = request.role_id == 1

    if request.method == "POST":
        serializer = CreateCustomRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return create_custom_request(serializer.validated_data, user_id=request.user_id)

    if request.method == "PUT":
        if not is_admin:
            return ADMIN_ONLY
        serializer = UpdateCustomRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return update_custom_request(serializer.validated_data, user_id=request.user_id)

    # A customer only ever sees their own requests; an admin sees all.
    return get_custom_requests(
        user_id=None if is_admin else request.user_id,
        request_id=request.GET.get("id"),
        page=request.GET.get("page", 1),
        page_size=request.GET.get("page_size", 10),
        request_status=request.GET.get("status"),
        search=request.GET.get("search_parameter")
    )


custom_requests.cls.throttle_scope = "custom_request"
