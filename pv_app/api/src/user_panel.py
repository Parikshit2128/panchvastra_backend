from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from helpers.middleware import user_authentication_required
from helpers.utils import generic_response_handler
from pv_app.api.business_logic.bl_user_panel import add_to_cart, create_address, create_category, create_coupon, create_notify_me_request, create_product, delete_address, delete_cart_item, delete_category, delete_coupon, delete_notify_me_request, delete_product, get_addresses, get_cart, get_categories, get_coupons, get_notify_me_requests, get_order_detail, get_order_listing, get_product_detail, get_product_listing, update_address, update_cart_quantity, update_category, update_coupon, update_product
from pv_app.api.serializer.sz_user_panel import AddToCartSerializer, CouponSerializer, CreateAddressSerializer, CreateCategorySerializer, CreateProductSerializer, NotifyMeSerializer, UpdateAddressSerializer, UpdateCartSerializer, UpdateCategorySerializer, UpdateCouponSerializer, UpdateProductSerializer
from pv_app.api.swagger.swag_user_panel import address_management_schema, categories_management_schema, products_management_schema, cart_management_schema, coupon_management_schema, notify_me_schema, orders_schema



@categories_management_schema
# @user_authentication_required(role_required=[1, 2])
@api_view(["GET", "POST", "PUT", "DELETE"])
@parser_classes([MultiPartParser, FormParser])
@generic_response_handler
def categories_management(request):

    # user_id = request.user_id
    user_id= 1

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
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))

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
# @user_authentication_required(role_required=[1, 2])
@api_view(["GET", "POST", "PUT", "DELETE"])
@generic_response_handler
def products_management(request):

    # user_id = request.user_id
    user_id = 1

    if request.method == "POST":

        serializer = CreateProductSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

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

        serializer = UpdateProductSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

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
@user_authentication_required(role_required=2)
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
@user_authentication_required(role_required=2)
@api_view(["GET", "POST", "PUT", "DELETE"])
@generic_response_handler
def coupon_management(request):
    user_id = request.user_id

    if request.method == "POST":
        serializer = CouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return create_coupon(serializer.validated_data, user_id)

    elif request.method == "GET":
        coupon_id = request.GET.get("id")
        coupon_code = request.GET.get("code")

        return get_coupons(
            user_id=user_id,
            coupon_id=coupon_id,
            coupon_code=coupon_code
        )

    elif request.method == "PUT":
        serializer = UpdateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return update_coupon(serializer.validated_data, user_id)

    elif request.method == "DELETE":
        coupon_id = request.GET.get("id")
        return delete_coupon(coupon_id, user_id)



@address_management_schema
@user_authentication_required(role_required=2)
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
@api_view(["GET", "POST", "DELETE"])
@generic_response_handler
def notify_me_management(request):

    if request.method == "POST":
        serializer = NotifyMeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return create_notify_me_request(
            serializer.validated_data
        )

    elif request.method == "GET":
        variant_size_id = request.GET.get("variant_size_id")
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))

        return get_notify_me_requests(
            variant_size_id=variant_size_id,
            page=page,
            page_size=page_size
        )

    elif request.method == "DELETE":
        notify_me_id = request.GET.get("id")
        email = request.GET.get("email")

        return delete_notify_me_request(
            notify_me_id,
            email
        )



@orders_schema
@user_authentication_required(role_required=2)
@api_view(["GET"])
@generic_response_handler
def orders(request):

    user_id = request.user_id
    # user_id= 1

    order_id = request.GET.get("id")
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))
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



