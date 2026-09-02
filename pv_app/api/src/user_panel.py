import json

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError
from rest_framework import status

from helpers.middleware import user_authentication_required
from helpers.utils import generic_response_handler, validate_image_files
from pv_app.api.business_logic.bl_user_panel import add_to_cart, create_address, create_category, create_coupon, create_notify_me_request, create_product, create_sub_category, delete_address, delete_cart_item, delete_category, delete_coupon, delete_notify_me_request, delete_product, delete_sub_category, get_addresses, get_cart, get_categories, get_coupons, get_notify_me_requests, get_order_detail, get_order_listing, get_product_detail, get_product_listing, get_sub_categories, update_address, update_cart_quantity, update_category, update_coupon, update_product, update_sub_category
from pv_app.api.serializer.sz_user_panel import AddToCartSerializer, CouponSerializer, CreateAddressSerializer, CreateCategorySerializer, CreateProductSerializer, CreateSubCategorySerializer, NotifyMeSerializer, UpdateAddressSerializer, UpdateCartSerializer, UpdateCategorySerializer, UpdateCouponSerializer, UpdateProductSerializer, UpdateSubCategorySerializer
from pv_app.api.swagger.swag_user_panel import address_management_schema, categories_management_schema, products_management_schema, cart_management_schema, coupon_management_schema, notify_me_schema, orders_schema, sub_categories_management_schema


def _parse_product_payload(request):
    """Product fields are normally sent as a plain JSON body. When the Admin
    panel needs to attach variant image files, it can't express a nested
    variants[].images list through multipart/form-data (multipart has no
    notion of nested list-of-dict fields), so it instead sends the same
    product/variant JSON as a string in a 'data' field alongside indexed
    file fields (variant_0_images, variant_1_images, ...). This returns
    (payload_dict, is_multipart) so the caller knows whether to also look
    for those indexed file fields.
    """
    content_type = request.content_type or ""

    if not content_type.startswith("multipart/form-data"):
        return request.data, False

    raw_payload = request.data.get("data")

    try:
        payload = json.loads(raw_payload) if raw_payload else {}
    except (TypeError, ValueError):
        raise ValidationError({"data": "Invalid JSON in 'data' field."})

    return payload, True


def _attach_variant_image_uploads(validated_data, request):
    """Pulls each variant's uploaded files out of request.FILES by that
    variant's position in the submitted 'variants' array (variant_<index>_images)
    and attaches the validated files onto that variant dict as 'new_images'
    for the business logic layer to upload/store.
    """
    for index, variant in enumerate(validated_data.get("variants", [])):
        uploads = request.FILES.getlist(f"variant_{index}_images")

        if uploads:
            variant["new_images"] = validate_image_files(uploads)



@categories_management_schema
@user_authentication_required(role_required=[1, 2], public_methods=["GET"])
@api_view(["GET", "POST", "PUT", "DELETE"])
@parser_classes([MultiPartParser, FormParser])
@generic_response_handler
def categories_management(request):

    user_id = request.user_id

    if request.method in ("POST", "PUT", "DELETE") and request.role_id != 1:
        return {
            "message": "You are not authorized to perform this action.",
            "data": {}
        }, status.HTTP_403_FORBIDDEN

    if request.method == "POST":
        serializer = CreateCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return create_category(
            serializer.validated_data,
            user_id
        )

    elif request.method == "GET":
        category_id = request.GET.get("id")
        search = request.GET.get("search_parameter")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)

        return get_categories(
            page,
            page_size,
            category_id,
            search
        )

    elif request.method == "PUT":
        serializer = UpdateCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return update_category(
            serializer.validated_data,
            user_id
        )

    elif request.method == "DELETE":
        category_id = request.GET.get("id")

        return delete_category(
            category_id,
            user_id
        )



@sub_categories_management_schema
@user_authentication_required(role_required=[1, 2], public_methods=["GET"])
@api_view(["GET", "POST", "PUT", "DELETE"])
@generic_response_handler
def sub_categories_management(request):

    if request.method in ("POST", "PUT", "DELETE") and request.role_id != 1:
        return {
            "message": "You are not authorized to perform this action.",
            "data": {}
        }, status.HTTP_403_FORBIDDEN

    if request.method == "POST":
        serializer = CreateSubCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return create_sub_category(
            serializer.validated_data
        )

    elif request.method == "GET":
        sub_category_id = request.GET.get("id")
        category_id = request.GET.get("category_id")
        search = request.GET.get("search_parameter")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)

        return get_sub_categories(
            page,
            page_size,
            sub_category_id,
            category_id,
            search
        )

    elif request.method == "PUT":
        serializer = UpdateSubCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return update_sub_category(
            serializer.validated_data
        )

    elif request.method == "DELETE":
        sub_category_id = request.GET.get("id")

        return delete_sub_category(
            sub_category_id
        )




# @products_management_schema
# @api_view(["GET"])
# @generic_response_handler
# def products_management(request):
#     print("request:", request.GET)
#     return get_products(
#         page=request.GET.get("page", 1),
#         page_size=request.GET.get("page_size", 20),
#         product_id=request.GET.get("id"),
#         category_id=request.GET.get("category_id"),
#         sub_category_id=request.GET.get("sub_category_id"),
#         size=request.GET.get("size"),
#         min_price=request.GET.get("min_price"),
#         max_price=request.GET.get("max_price"),
#         search=request.GET.get("search"),
#         sort_by=request.GET.get("sort_by", "latest"),
#         tag=request.GET.get("tag"),
#     )

# @products_management_schema
# @api_view(["GET"])
# @generic_response_handler
# def products_management(request):

#     product_id = request.GET.get("id")

#     if product_id:
#         return get_product_detail(
#             product_id=product_id
#         )

#     return get_product_listing(
#         page=request.GET.get("page", 1),
#         page_size=request.GET.get("page_size", 20),
#         category_id=request.GET.get("category_id"),
#         sub_category_id=request.GET.get("sub_category_id"),
#         tag=request.GET.get("tag"),
#         color=request.GET.get("color"),
#         size=request.GET.get("size"),
#         min_price=request.GET.get("min_price"),
#         max_price=request.GET.get("max_price"),
#         search=request.GET.get("search"),
#         sort_by=request.GET.get("sort_by", "latest")
#     )



@products_management_schema
@user_authentication_required(role_required=[1, 2], public_methods=["GET"])
@api_view(["GET", "POST", "PUT", "DELETE"])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@generic_response_handler
def products_management(request):

    user_id = request.user_id

    if request.method in ("POST", "PUT", "DELETE") and request.role_id != 1:
        return {
            "message": "You are not authorized to perform this action.",
            "data": {}
        }, status.HTTP_403_FORBIDDEN

    if request.method == "POST":

        payload, is_multipart = _parse_product_payload(request)

        serializer = CreateProductSerializer(
            data=payload
        )
        serializer.is_valid(raise_exception=True)

        if is_multipart:
            _attach_variant_image_uploads(serializer.validated_data, request)

        return create_product(
            serializer.validated_data,
            user_id
        )

    elif request.method == "GET":

        product_id = request.GET.get("id")

        if product_id:
            return get_product_detail(
                product_id=product_id
            )

        return get_product_listing(
            page=request.GET.get("page", 1),
            page_size=request.GET.get("page_size", 20),
            category_id=request.GET.get("category_id"),
            sub_category_id=request.GET.get("sub_category_id"),
            tag=request.GET.get("tag"),
            color=request.GET.get("color"),
            size=request.GET.get("size"),
            min_price=request.GET.get("min_price"),
            max_price=request.GET.get("max_price"),
            search=request.GET.get("search"),
            sort_by=request.GET.get("sort_by", "latest")
        )

    elif request.method == "PUT":

        payload, is_multipart = _parse_product_payload(request)

        serializer = UpdateProductSerializer(
            data=payload
        )
        serializer.is_valid(raise_exception=True)

        if is_multipart:
            _attach_variant_image_uploads(serializer.validated_data, request)

        return update_product(
            serializer.validated_data,
            user_id
        )

    elif request.method == "DELETE":

        product_id = request.GET.get("id")

        return delete_product(
            product_id,
            user_id
        )



# @products_management_schema
# # @user_authentication_required(role_required=[1, 2])
# @api_view(["GET", "POST", "PUT", "DELETE"])
# @generic_response_handler
# def products_management(request):

#     # user_id = request.user_id
#     user_id = 1

#     if request.method == "POST":

#         serializer = CreateProductSerializer(
#             data=request.data
#         )
#         serializer.is_valid(raise_exception=True)

#         return create_product(
#             serializer.validated_data,
#             user_id
#         )

#     elif request.method == "GET":

#         product_id = request.GET.get("id")

#         if product_id:
#             return get_product_detail(
#                 product_id=product_id
#             )

#         return get_product_listing(
#             page=request.GET.get("page", 1),
#             page_size=request.GET.get("page_size", 20),
#             category_id=request.GET.get("category_id"),
#             sub_category_id=request.GET.get("sub_category_id"),
#             tag=request.GET.get("tag"),
#             color=request.GET.get("color"),
#             size=request.GET.get("size"),
#             min_price=request.GET.get("min_price"),
#             max_price=request.GET.get("max_price"),
#             search=request.GET.get("search"),
#             sort_by=request.GET.get("sort_by", "latest")
#         )

#     elif request.method == "PUT":

#         serializer = UpdateProductSerializer(
#             data=request.data
#         )
#         serializer.is_valid(raise_exception=True)

#         return update_product(
#             serializer.validated_data,
#             user_id
#         )

#     elif request.method == "DELETE":

#         product_id = request.GET.get("id")

#         return delete_product(
#             product_id,
#             user_id
#         )


@cart_management_schema
@user_authentication_required(role_required=[1, 2])
@api_view(["GET", "POST", "PUT", "DELETE"])
@generic_response_handler
def cart_management(request):
    
    user_id = request.user_id
    # user_id = 1 

    if request.method == "POST":
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return add_to_cart(serializer.validated_data, user_id)

    elif request.method == "GET":
        return get_cart(user_id)

    elif request.method == "PUT":
        serializer = UpdateCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return update_cart_quantity(serializer.validated_data, user_id)

    elif request.method == "DELETE":
        cart_item_id = request.GET.get("id")
        return delete_cart_item(cart_item_id, user_id)



@coupon_management_schema
@user_authentication_required(role_required=[1, 2])
@api_view(["GET", "POST", "PUT", "DELETE"])
@generic_response_handler
def coupon_management(request):
    user_id = request.user_id
    is_admin = request.role_id == 1

    if request.method in ("POST", "PUT", "DELETE") and not is_admin:
        return {
            "message": "You are not authorized to perform this action.",
            "data": {}
        }, status.HTTP_403_FORBIDDEN

    if request.method == "POST":
        serializer = CouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return create_coupon(serializer.validated_data, user_id)

    elif request.method == "GET":
        coupon_id = request.GET.get("id")
        coupon_code = request.GET.get("code")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)

        return get_coupons(
            user_id=user_id,
            coupon_id=coupon_id,
            coupon_code=coupon_code,
            page=page,
            page_size=page_size,
            admin_view=is_admin
        )

    elif request.method == "PUT":
        serializer = UpdateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return update_coupon(serializer.validated_data, user_id)

    elif request.method == "DELETE":
        coupon_id = request.GET.get("id")
        return delete_coupon(coupon_id, user_id)



@address_management_schema
@user_authentication_required(role_required=[1, 2])
@api_view(["GET", "POST", "PUT", "DELETE"])
@generic_response_handler
def address_management(request):

    user_id = request.user_id

    if request.method == "POST":
        serializer = CreateAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return create_address(
            serializer.validated_data,
            user_id
        )

    elif request.method == "GET":
        address_id = request.GET.get("id")

        return get_addresses(
            user_id=user_id,
            address_id=address_id
        )

    elif request.method == "PUT":
        serializer = UpdateAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return update_address(
            serializer.validated_data,
            user_id
        )

    elif request.method == "DELETE":
        address_id = request.GET.get("id")

        return delete_address(
            address_id,
            user_id
        )



@notify_me_schema
@user_authentication_required(role_required=[1, 2])
@api_view(["GET", "POST", "DELETE"])
@generic_response_handler
def notify_me_management(request):

    is_admin = request.role_id == 1

    if request.method == "POST":
        serializer = NotifyMeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return create_notify_me_request(
            serializer.validated_data,
            user_id=request.user_id
        )

    elif request.method == "GET":
        variant_size_id = request.GET.get("variant_size_id")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)

        return get_notify_me_requests(
            variant_size_id=variant_size_id,
            page=page,
            page_size=page_size,
            user_id=None if is_admin else request.user_id
        )

    elif request.method == "DELETE":
        notify_me_id = request.GET.get("id")

        return delete_notify_me_request(
            notify_me_id,
            user_id=None if is_admin else request.user_id
        )



@orders_schema
@user_authentication_required(role_required=[1, 2])
@api_view(["GET"])
@generic_response_handler
def orders(request):

    user_id = request.user_id
    # user_id= 1

    order_id = request.GET.get("id")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 10)
    order_type=request.GET.get("order_type")
    

    if order_id:
        return get_order_detail(
            user_id=user_id,
            order_id=order_id
        )

    return get_order_listing(
        user_id=user_id,
        page=page,
        page_size=page_size,
        order_type=order_type
    )



