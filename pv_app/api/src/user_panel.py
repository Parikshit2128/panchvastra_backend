from rest_framework.decorators import api_view
from rest_framework import status

from helpers.utils import generic_response_handler
from pv_app.api.business_logic.bl_user_panel import create_category, delete_category, get_categories, get_products, update_category
from pv_app.api.serializer.sz_user_panel import CreateCategorySerializer, UpdateCategorySerializer
from pv_app.api.swagger.swag_user_panel import categories_management_schema, products_management_schema



@categories_management_schema
# @user_authentication_required(
#     role_required=(settings.FINANCE_ADMIN_ID, settings.PLATFORM_VIEWER)
# )
@api_view(["GET", "POST", "PUT", "DELETE"])
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
    


@products_management_schema
@api_view(["GET"])
@generic_response_handler
def products_management(request):

    return get_products(
        page=request.GET.get("page", 1),
        page_size=request.GET.get("page_size", 20),
        product_id=request.GET.get("id"),
        category_id=request.GET.get("category_id"),
        sub_category_id=request.GET.get("sub_category_id"),
        size=request.GET.get("size"),
        min_price=request.GET.get("min_price"),
        max_price=request.GET.get("max_price"),
        search=request.GET.get("search"),
        sort_by=request.GET.get("sort_by", "latest")
    )