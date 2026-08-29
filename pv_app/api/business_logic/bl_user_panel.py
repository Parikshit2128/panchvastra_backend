import json
import math

from django.db import connection
from rest_framework import status
from django.db import transaction
from helpers.utils import db_query_result_to_json, delete_image_from_imagekit, paginate_queryset, send_restock_notification_email, upload_image_to_imagekit

def create_category(data, user_id):

    name = data.get("name")
    description = data.get("description")
    image = data.get("image")
    is_active = data.get("is_active", True)

    image_url = None
    imagekit_file_id = None

    if image:
        uploaded_image = upload_image_to_imagekit(
            image=image,
            folder="/categories"
        )

        image_url = uploaded_image["url"]
        imagekit_file_id = uploaded_image["file_id"]

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT 1
            FROM categories
            WHERE LOWER(name) = LOWER(%s)
            AND is_deleted = FALSE
            """,
            [name]
        )

        if cursor.fetchone():
            return {
                "message": "Category already exists.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        cursor.execute(
            """
            INSERT INTO categories
            (
                name,
                description,
                image_url,
                imagekit_file_id,
                is_active,
                created_by,
                updated_by,
                created_at,
                updated_at
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW(),
                NOW()
            )
            RETURNING id
            """,
            [
                name,
                description,
                image_url,
                imagekit_file_id,
                is_active,
                user_id,
                user_id
            ]
        )

        category_id = cursor.fetchone()[0]

        connection.commit()

    category_data, _ = get_categories(
        page=1,
        page_size=1,
        category_id=category_id
    )

    return {
        "message": "Category created successfully.",
        "data": category_data.get("data")
    }, status.HTTP_201_CREATED



def get_categories(
    page=1,
    page_size=10,
    category_id=None,
    search=None
):

    select_columns = [
        "id",
        "name",
        "description",
        "image_url",
        "is_active",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by"
    ]

    columns_str = ", ".join(select_columns)

    params = []

    where_clause = """
        WHERE is_deleted = FALSE
    """

    if category_id:
        where_clause += " AND id = %s"
        params.append(category_id)

    if search:
        where_clause += " AND name ILIKE %s"
        params.append(f"%{search}%")

    sql = f"""
        SELECT {columns_str}
        FROM categories
        {where_clause}
        ORDER BY created_at DESC
    """

    with connection.cursor() as cursor:

        cursor.execute(sql, params)

        rows = cursor.fetchall()

        if not rows:
            return {
                "message": "Data not found.",
                "data": []
            }, (
                status.HTTP_404_NOT_FOUND
                if category_id
                else status.HTTP_200_OK
            )

        result = [
            db_query_result_to_json(
                row,
                select_columns
            )
            for row in rows
        ]

        paginated_list, pagination = paginate_queryset(
            result,
            page,
            page_size
        )

        if category_id:
            return {
                "message": "Data fetched successfully.",
                "data": paginated_list[0]
            }, status.HTTP_200_OK

        return {
            "message": "Data fetched successfully.",
            "data": paginated_list,
            "pagination": pagination
        }, status.HTTP_200_OK
    


def update_category(data, user_id):

    category_id = data.get("id")

    image = data.get("image")

    updatable_fields = [
        "name",
        "description",
        "is_active"
    ]

    set_parts = []
    values = []

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT imagekit_file_id
            FROM categories
            WHERE id = %s
            AND is_deleted = FALSE
            """,
            [category_id]
        )

        row = cursor.fetchone()

        if not row:
            return {
                "message": "Category not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        old_file_id = row[0]

    for field in updatable_fields:

        if field in data:

            if field == "name":

                with connection.cursor() as cursor:

                    cursor.execute(
                        """
                        SELECT 1
                        FROM categories
                        WHERE LOWER(name) = LOWER(%s)
                        AND id <> %s
                        AND is_deleted = FALSE
                        """,
                        [
                            data[field],
                            category_id
                        ]
                    )

                    if cursor.fetchone():
                        return {
                            "message": "Category already exists.",
                            "data": {}
                        }, status.HTTP_400_BAD_REQUEST

            set_parts.append(f"{field} = %s")
            values.append(data[field])

    if image:

        if old_file_id:
            delete_image_from_imagekit(old_file_id)

        uploaded = upload_image_to_imagekit(
            image=image,
            folder="/categories"
        )

        set_parts.append("image_url = %s")
        values.append(uploaded["url"])

        set_parts.append("imagekit_file_id = %s")
        values.append(uploaded["file_id"])

    if not set_parts:
        return {
            "message": "No fields to update.",
            "data": {}
        }, status.HTTP_400_BAD_REQUEST

    set_parts.append("updated_by = %s")
    values.append(user_id)

    set_parts.append("updated_at = NOW()")

    values.append(category_id)

    sql = f"""
        UPDATE categories
        SET {', '.join(set_parts)}
        WHERE id = %s
        AND is_deleted = FALSE
    """

    with connection.cursor() as cursor:

        cursor.execute(sql, values)

        if cursor.rowcount == 0:
            return {
                "message": "Category not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        connection.commit()

    category_data, _ = get_categories(
        page=1,
        page_size=1,
        category_id=category_id
    )

    return {
        "message": "Category updated successfully.",
        "data": category_data.get("data")
    }, status.HTTP_200_OK


def delete_category(category_id, user_id):

    if not category_id:
        return {
            "message": "id is required.",
            "data": {}
        }, status.HTTP_400_BAD_REQUEST

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT imagekit_file_id
            FROM categories
            WHERE id = %s
            AND is_deleted = FALSE
            """,
            [category_id]
        )

        row = cursor.fetchone()

        if not row:
            return {
                "message": "Category not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        imagekit_file_id = row[0]

        cursor.execute(
            """
            UPDATE categories
            SET
                is_deleted = TRUE,
                updated_by = %s,
                updated_at = NOW()
            WHERE id = %s
            AND is_deleted = FALSE
            """,
            [
                user_id,
                category_id
            ]
        )

        connection.commit()

    if imagekit_file_id:
        try:
            delete_image_from_imagekit(imagekit_file_id)
        except Exception:
            pass

    return {
        "message": "Category deleted successfully.",
        "data": {}
    }, status.HTTP_200_OK


VALID_TAGS = {
    "trending",
    "best-sellers",
    "new-arrivals",
    "hot-deals"
}



# def get_products(
#     page=1,
#     page_size=20,
#     product_id=None,
#     category_id=None,
#     sub_category_id=None,
#     size=None,
#     min_price=None,
#     max_price=None,
#     search=None,
#     sort_by="latest",
#     tag=None
# ):      

#     page = max(int(page), 1)
#     page_size = max(int(page_size), 1)

#     where_conditions = [
#         "p.is_deleted = FALSE",
#         "p.is_active = TRUE"
#     ]

#     params = []

#     if product_id:
#         where_conditions.append("p.id = %s")
#         params.append(product_id)

#     if category_id:
#         where_conditions.append("p.category_id = %s")
#         params.append(category_id)

#     if sub_category_id:
#         where_conditions.append("p.sub_category_id = %s")
#         params.append(sub_category_id)

#     if tag:
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT id
#                 FROM product_tags
#                 WHERE LOWER(name) = %s
#                 AND is_deleted = FALSE
#                 AND is_active = TRUE
#             """, [tag])

#             tag_row = cursor.fetchone()

#         if not tag_row:
#             return {
#                 "message": "Invalid tag.",
#                 "data": []
#             }, status.HTTP_400_BAD_REQUEST

#         where_conditions.append("p.tag_id = %s")
#         params.append(tag_row[0])


#     # For size stored as: S,M,L,XL
#     if size:
#         where_conditions.append(
#             """
#             EXISTS (
#                 SELECT 1
#                 FROM unnest(
#                     string_to_array(
#                         REPLACE(p.size, ' ', ''),
#                         ','
#                     )
#                 ) sz
#                 WHERE LOWER(sz) = LOWER(%s)
#             )
#             """
#         )
#         params.append(size)

#     if min_price:
#         where_conditions.append(
#             "p.selling_price >= %s"
#         )
#         params.append(min_price)

#     if max_price:
#         where_conditions.append(
#             "p.selling_price <= %s"
#         )
#         params.append(max_price)

#     if search:
#         where_conditions.append(
#             """
#             (
#                 p.name ILIKE %s
#                 OR p.description ILIKE %s
#                 OR p.fabric ILIKE %s
#                 OR p.color ILIKE %s
#             )
#             """
#         )

#         search_term = f"%{search}%"

#         params.extend([
#             search_term,
#             search_term,
#             search_term,
#             search_term
#         ])

#     where_clause = " AND ".join(where_conditions)

#     sort_mapping = {
#         "price_low_to_high": "p.selling_price ASC",
#         "price_high_to_low": "p.selling_price DESC",
#         "latest": "p.created_at DESC",
#         "oldest": "p.created_at ASC"
#     }

#     order_by = sort_mapping.get(
#         sort_by,
#         "p.created_at DESC"
#     )

#     # ------------------------
#     # Total Count
#     # ------------------------

#     count_sql = f"""
#         SELECT COUNT(DISTINCT p.id)
#         FROM products p
#         WHERE {where_clause}
#     """

#     with connection.cursor() as cursor:

#         cursor.execute(count_sql, params)

#         total_records = cursor.fetchone()[0]

#         if total_records == 0:
#             return {
#                 "message": "Data not found.",
#                 "data": []
#             }, status.HTTP_200_OK

#     offset = (page - 1) * page_size

#     # ------------------------
#     # Main Query
#     # ------------------------

#     sql = f"""
#         SELECT
#             p.id,
#             p.name,
#             p.description,
#             p.fabric,
#             p.gsm,
#             p.color,
#             p.size,
#             p.mrp,
#             p.selling_price,
#             p.cost_price,
#             p.stock_quantity,
#             p.is_featured,
#             p.is_new_arrival,
#             p.created_at,

#             c.id AS category_id,
#             c.name AS category_name,

#             sc.id AS sub_category_id,
#             sc.name AS sub_category_name,

#             pt.id AS tag_id,
#             pt.name AS tag_name,

#             COALESCE(
#                 json_agg(
#                     json_build_object(
#                         'id', pi.id,
#                         'image_url', pi.image_url,
#                         'display_order', pi.display_order
#                     )
#                     ORDER BY pi.display_order
#                 ) FILTER (
#                     WHERE pi.id IS NOT NULL
#                 ),
#                 '[]'
#             ) AS images

#         FROM products p

#         INNER JOIN categories c
#             ON c.id = p.category_id
#             AND c.is_deleted = FALSE

#         INNER JOIN sub_categories sc
#             ON sc.id = p.sub_category_id
#             AND sc.is_deleted = FALSE

#         INNER JOIN product_tags pt
#             ON pt.id = p.tag_id
#             AND pt.is_deleted = FALSE

#         LEFT JOIN product_images pi
#             ON pi.product_id = p.id
#             AND pi.is_deleted = FALSE
#             AND pi.is_active = TRUE

#         WHERE {where_clause}

#         GROUP BY
#             p.id,
#             c.id,
#             sc.id,
#             pt.id

#         ORDER BY {order_by}

#         LIMIT %s
#         OFFSET %s
#     """

#     query_params = params + [
#         page_size,
#         offset
#     ]

#     with connection.cursor() as cursor:

#         cursor.execute(sql, query_params)

#         rows = cursor.fetchall()

#         columns = [
#             "id",
#             "name",
#             "description",
#             "fabric",
#             "gsm",
#             "color",
#             "size",
#             "mrp",
#             "selling_price",
#             "cost_price",
#             "stock_quantity",
#             "is_featured",
#             "is_new_arrival",
#             "created_at",
#             "category_id",
#             "category_name",
#             "sub_category_id",
#             "sub_category_name",
#             "tag_id",
#             "tag_name",
#             "images"
#         ]

#         result = []

#         for row in rows:

#             item = dict(zip(columns, row))

#             item["discount_percentage"] = (
#                 round(
#                     (
#                         (
#                             float(item["mrp"])
#                             - float(item["selling_price"])
#                         )
#                         / float(item["mrp"])
#                     ) * 100
#                 )
#                 if item["mrp"] and item["mrp"] > 0
#                 else 0
#             )

#             item["discount_amount"] = (
#                 float(item["mrp"]) -
#                 float(item["selling_price"])
#             )

#             item["in_stock"] = item["stock_quantity"] > 0
                        
#             item["category"] = {
#                 "id": item.pop("category_id"),
#                 "name": item.pop("category_name")
#             }

#             item["sub_category"] = {
#                 "id": item.pop("sub_category_id"),
#                 "name": item.pop("sub_category_name")
#             }

#             item["tag"] = {
#                 "id": item.pop("tag_id"),
#                 "name": item.pop("tag_name")
#             }

#             if isinstance(item["images"], str):
#                 item["images"] = json.loads(
#                     item["images"]
#                 )

#             item["primary_image"] = (
#                 item["images"][0]["image_url"]
#                 if item["images"]
#                 else None
#             )

#             result.append(item)

#     if product_id:

#         return {
#             "message": "Data fetched successfully.",
#             "data": result[0] if result else {}
#         }, status.HTTP_200_OK

#     pagination = {
#         "page": page,
#         "page_size": page_size,
#         "total_records": total_records,
#         "total_pages": math.ceil(
#             total_records / page_size
#         ),
#         "has_next": (
#             page * page_size
#         ) < total_records,
#         "has_previous": page > 1
#     }

#     return {
#         "message": "Data fetched successfully.",
#         "data": result,
#         "pagination": pagination
#     }, status.HTTP_200_OK


def get_product_listing(
    page=1,
    page_size=20,
    category_id=None,
    sub_category_id=None,
    tag=None,
    color=None,
    size=None,
    min_price=None,
    max_price=None,
    search=None,
    sort_by="latest"
):
    page = max(int(page), 1)
    page_size = max(int(page_size), 1)
    offset = (page - 1) * page_size

    # Base where conditions
    where_conditions = ["p.is_deleted = FALSE", "p.is_active = TRUE"]
    params = []

    # Filter by Category / Sub-Category
    if category_id:
        where_conditions.append("p.category_id = %s")
        params.append(category_id)
    if sub_category_id:
        where_conditions.append("p.sub_category_id = %s")
        params.append(sub_category_id)

    # Filter by Variant Attributes (Color / Size / Price)
    variant_conditions = ["v.is_deleted = FALSE", "v.is_active = TRUE"]
    variant_params = []

    if color:
        variant_conditions.append("LOWER(v.color) = LOWER(%s)")
        variant_params.append(color)
    if min_price:
        variant_conditions.append("v.selling_price >= %s")
        variant_params.append(min_price)
    if max_price:
        variant_conditions.append("v.selling_price <= %s")
        variant_params.append(max_price)
    if size:
        variant_conditions.append("""
            EXISTS (
                SELECT 1 FROM public.product_variant_sizes pvs 
                WHERE pvs.variant_id = v.id 
                AND LOWER(pvs.size) = LOWER(%s) 
                AND pvs.is_active = TRUE AND pvs.is_deleted = FALSE
            )
        """)
        variant_params.append(size)

    if len(variant_conditions) > 2 or color or min_price or max_price or size:
        where_conditions.append(f"""
            EXISTS (
                SELECT 1 FROM public.product_variants v 
                WHERE v.product_id = p.id AND {" AND ".join(variant_conditions)}
            )
        """)
        params.extend(variant_params)

    if tag:
        where_conditions.append("""
            EXISTS (
                SELECT 1 FROM public.product_tag_mapping ptm
                JOIN public.product_tags pt ON pt.id = ptm.tag_id
                WHERE ptm.product_id = p.id 
                AND LOWER(pt.name) = LOWER(%s)
                AND ptm.is_active = TRUE AND ptm.is_deleted = FALSE
                AND pt.is_active = TRUE AND pt.is_deleted = FALSE
            )
        """)
        params.append(tag)

    if search:
        where_conditions.append("""
            (
                p.name ILIKE %s 
                OR p.description ILIKE %s 
                OR p.fabric ILIKE %s
                OR EXISTS (
                    SELECT 1 FROM public.product_variants v 
                    WHERE v.product_id = p.id AND v.color ILIKE %s
                )
            )
        """)
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term])

    where_clause = " AND ".join(where_conditions)

    sort_mapping = {
        "price_low_to_high": "min_selling_price ASC",
        "price_high_to_low": "min_selling_price DESC",
        "latest": "p.created_at DESC",
        "oldest": "p.created_at ASC"
    }
    order_by = sort_mapping.get(sort_by, "p.created_at DESC")

    count_sql = f"SELECT COUNT(*) FROM public.products p WHERE {where_clause}"
    with connection.cursor() as cursor:
        cursor.execute(count_sql, params)
        total_records = cursor.fetchone()[0]

    if total_records == 0:
        return {"message": "Data not found.", "data": [], "pagination": {}}, status.HTTP_200_OK

    main_sql = f"""
        SELECT 
            p.id, p.name, p.description, p.fabric, p.gsm, p.is_featured, p.is_new_arrival, p.created_at,
            c.id AS category_id, c.name AS category_name,
            sc.id AS sub_category_id, sc.name AS sub_category_name,
            
            -- Subquery to aggregate tags
            (
                SELECT COALESCE(json_agg(json_build_object('id', t.id, 'name', t.name)), '[]')
                FROM public.product_tag_mapping m
                JOIN public.product_tags t ON t.id = m.tag_id
                WHERE m.product_id = p.id AND m.is_deleted = FALSE AND m.is_active = TRUE
            ) AS tags,

            -- Extract tracking variant data (Default variant, fallback to cheapest variant)
            v.id AS variant_id, v.sku, v.color, v.mrp, v.selling_price,
            
            -- Primary Image for thumbnail
            (
                SELECT image_url FROM public.product_variant_images img 
                WHERE img.variant_id = v.id AND img.is_deleted = FALSE AND img.is_active = TRUE
                ORDER BY img.display_order ASC LIMIT 1
            ) AS primary_image,
            
            -- Sort metric helper
            (SELECT MIN(selling_price) FROM public.product_variants WHERE product_id = p.id AND is_deleted = FALSE) as min_selling_price

        FROM public.products p
        INNER JOIN public.categories c ON c.id = p.category_id AND c.is_deleted = FALSE
        LEFT JOIN public.sub_categories sc ON sc.id = p.sub_category_id AND sc.is_deleted = FALSE
        
        -- Join single matching display variant (optimized laterally)
        LEFT JOIN LATERAL (
            SELECT * FROM public.product_variants pv 
            WHERE pv.product_id = p.id AND pv.is_deleted = FALSE AND pv.is_active = TRUE
            ORDER BY pv.is_default DESC, pv.selling_price ASC LIMIT 1
        ) v ON TRUE

        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    """

    query_params = params + [page_size, offset]

    with connection.cursor() as cursor:
        cursor.execute(main_sql, query_params)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    result = []
    for row in rows:
        item = dict(zip(columns, row))
        
        mrp = float(item["mrp"]) if item["mrp"] else 0.0
        selling_price = float(item["selling_price"]) if item["selling_price"] else 0.0
        
        item["discount_amount"] = round(mrp - selling_price, 2)
        item["discount_percentage"] = round((item["discount_amount"] / mrp) * 100) if mrp > 0 else 0

        item["category"] = {"id": item.pop("category_id"), "name": item.pop("category_name")}
        item["sub_category"] = {"id": item.pop("sub_category_id"), "name": item.pop("sub_category_name")} if item["sub_category_id"] else None
        item["tags"] = json.loads(item["tags"]) if isinstance(item["tags"], str) else item["tags"]
        
        item.pop("min_selling_price", None)
        result.append(item)

    pagination = {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": math.ceil(total_records / page_size),
        "has_next": (page * page_size) < total_records,
        "has_previous": page > 1
    }

    return {"message": "Data fetched successfully.", "data": result, "pagination": pagination}, status.HTTP_200_OK


def get_product_detail(product_id):

    sql = """
        SELECT 
            p.id, p.name, p.description, p.fabric, p.gsm, p.is_featured, p.is_new_arrival, p.created_at, p.key_highlights,
            c.id AS category_id, c.name AS category_name,
            sc.id AS sub_category_id, sc.name AS sub_category_name,
            
            -- Structural Meta JSON build for product variants hierarchy
            (
                SELECT COALESCE(json_agg(json_build_object(
                    'id', v.id,
                    'sku', v.sku,
                    'color', v.color,
                    'mrp', v.mrp,
                    'selling_price', v.selling_price,
                    'cost_price', v.cost_price,
                    'is_default', v.is_default,
                    'images', (
                        SELECT COALESCE(json_agg(json_build_object(
                            'id', img.id,
                            'image_url', img.image_url,
                            'display_order', img.display_order
                        ) ORDER BY img.display_order ASC), '[]')
                        FROM public.product_variant_images img 
                        WHERE img.variant_id = v.id AND img.is_deleted = FALSE AND img.is_active = TRUE
                    ),
                    'sizes', (
                        SELECT COALESCE(json_agg(json_build_object(
                            'id', sz.id,
                            'size', sz.size,
                            'stock_quantity', sz.stock_quantity,
                            'in_stock', (sz.stock_quantity > 0)
                        )), '[]')
                        FROM public.product_variant_sizes sz
                        WHERE sz.variant_id = v.id AND sz.is_deleted = FALSE AND sz.is_active = TRUE
                    )
                )), '[]')
                FROM public.product_variants v
                WHERE v.product_id = p.id AND v.is_deleted = FALSE AND v.is_active = TRUE
            ) AS variants,

            -- Tags array
            (
                SELECT COALESCE(json_agg(json_build_object('id', t.id, 'name', t.name)), '[]')
                FROM public.product_tag_mapping m
                JOIN public.product_tags t ON t.id = m.tag_id
                WHERE m.product_id = p.id AND m.is_deleted = FALSE AND m.is_active = TRUE
            ) AS tags

        FROM public.products p
        INNER JOIN public.categories c ON c.id = p.category_id AND c.is_deleted = FALSE
        LEFT JOIN public.sub_categories sc ON sc.id = p.sub_category_id AND sc.is_deleted = FALSE
        WHERE p.id = %s AND p.is_deleted = FALSE AND p.is_active = TRUE
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [product_id])
        row = cursor.fetchone()
        if not row:
            return {"message": "Product not found.", "data": {}}, status.HTTP_404_NOT_FOUND
        
        columns = [col[0] for col in cursor.description]
        item = dict(zip(columns, row))

    item["category"] = {"id": item.pop("category_id"), "name": item.pop("category_name")}
    item["sub_category"] = {"id": item.pop("sub_category_id"), "name": item.pop("sub_category_name")} if item["sub_category_id"] else None
    item["variants"] = json.loads(item["variants"]) if isinstance(item["variants"], str) else item["variants"]
    item["tags"] = json.loads(item["tags"]) if isinstance(item["tags"], str) else item["tags"]
    item["key_highlights"] = item.get("key_highlights") or {}

    for v in item["variants"]:
        mrp = float(v["mrp"])
        sp = float(v["selling_price"])
        v["discount_amount"] = round(mrp - sp, 2)
        v["discount_percentage"] = round((v["discount_amount"] / mrp) * 100) if mrp > 0 else 0
        v["total_stock"] = sum(s["stock_quantity"] for s in v["sizes"])
        v["in_stock"] = v["total_stock"] > 0

    return {"message": "Data fetched successfully.", "data": item}, status.HTTP_200_OK



def add_to_cart(validated_data, user_id):
    variant_size_id = validated_data["variant_size_id"]
    quantity = validated_data["quantity"]

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT stock_quantity 
            FROM public.product_variant_sizes 
            WHERE id = %s AND is_active = TRUE AND is_deleted = FALSE
        """, [variant_size_id])
        
        row = cursor.fetchone()
        if not row:
            return {"message": "Selected product size variant is unavailable."}, status.HTTP_404_NOT_FOUND
        
        available_stock = row[0]
        if available_stock < quantity:
            return {"message": f"Insufficient stock. Only {available_stock} items left."}, status.HTTP_400_BAD_REQUEST

        cursor.execute("""
            INSERT INTO public.cart_items (user_id, variant_size_id, quantity, created_by, updated_by)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, variant_size_id) 
            DO UPDATE SET 
                quantity = public.cart_items.quantity + EXCLUDED.quantity,
                is_deleted = FALSE,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = EXCLUDED.updated_by
            RETURNING id, quantity;
        """, [user_id, variant_size_id, quantity, user_id, user_id])
        
        cart_id, final_quantity = cursor.fetchone()

        if final_quantity > available_stock:
            cursor.execute("""
                UPDATE public.cart_items SET quantity = %s WHERE id = %s
            """, [available_stock, cart_id])
            return {"message": f"Cart adjusted to maximum available stock ({available_stock})."}, status.HTTP_200_OK

    return {"message": "Item added to cart successfully."}, status.HTTP_201_CREATED


def get_cart(user_id):
    sql = """
        SELECT 
            ci.id AS cart_item_id,
            ci.quantity,
            p.id AS product_id,
            p.name AS product_name,
            v.color,
            pvs.size,
            v.mrp,
            v.selling_price,
            (v.mrp - v.selling_price) AS discount_amount,
            pvs.stock_quantity AS available_stock,
            (pvs.stock_quantity > 0 AND pvs.is_active = TRUE) AS is_in_stock,
            (
                SELECT image_url FROM public.product_variant_images img 
                WHERE img.variant_id = v.id AND img.is_deleted = FALSE AND img.is_active = TRUE
                ORDER BY img.display_order ASC LIMIT 1
            ) AS primary_image
        FROM public.cart_items ci
        INNER JOIN public.product_variant_sizes pvs ON pvs.id = ci.variant_size_id
        INNER JOIN public.product_variants v ON v.id = pvs.variant_id
        INNER JOIN public.products p ON p.id = v.product_id
        WHERE ci.user_id = %s AND ci.is_deleted = FALSE AND ci.is_active = TRUE
        ORDER BY ci.created_at DESC;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    cart_items = []
    total_mrp = 0.0
    total_selling_price = 0.0

    for row in rows:
        item = dict(zip(columns, row))
        
        item["mrp"] = float(item["mrp"])
        item["selling_price"] = float(item["selling_price"])
        item["discount_amount"] = round(float(item["discount_amount"]), 2)
        
        if item["is_in_stock"]:
            total_mrp += item["mrp"] * item["quantity"]
            total_selling_price += item["selling_price"] * item["quantity"]

        cart_items.append(item)

    cart_summary = {
        "items": cart_items,
        "summary": {
            "total_mrp": round(total_mrp, 2),
            "total_discount": round(total_mrp - total_selling_price, 2),
            "subtotal": round(total_selling_price, 2),
            "item_count": sum(i["quantity"] for i in cart_items if i["is_in_stock"])
        }
    }

    return {"message": "Cart retrieved successfully.", "data": cart_summary}, status.HTTP_200_OK


def update_cart_quantity(validated_data, user_id):
    cart_item_id = validated_data["cart_item_id"]
    new_quantity = validated_data["quantity"]

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT pvs.stock_quantity, pvs.is_active, pvs.is_deleted
            FROM public.cart_items ci
            JOIN public.product_variant_sizes pvs ON pvs.id = ci.variant_size_id
            WHERE ci.id = %s AND ci.user_id = %s AND ci.is_deleted = FALSE
        """, [cart_item_id, user_id])
        
        stock_row = cursor.fetchone()
        if not stock_row or stock_row[1] is False or stock_row[2] is True:
            return {"message": "Cart item metadata is invalid or inactive."}, status.HTTP_404_NOT_FOUND

        if stock_row[0] < new_quantity:
            return {"message": f"Cannot update quantity. Only {stock_row[0]} units available."}, status.HTTP_400_BAD_REQUEST

        cursor.execute("""
            UPDATE public.cart_items 
            SET quantity = %s, updated_at = CURRENT_TIMESTAMP, updated_by = %s
            WHERE id = %s AND user_id = %s;
        """, [new_quantity, user_id, cart_item_id, user_id])

    return {"message": "Cart quantity updated successfully."}, status.HTTP_200_OK


def delete_cart_item(cart_item_id, user_id):
    if not cart_item_id:
        return {"message": "Cart item ID parameter 'id' is required."}, status.HTTP_400_BAD_REQUEST

    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE public.cart_items 
            SET quantity = 0, is_deleted = TRUE, is_active = FALSE, updated_at = CURRENT_TIMESTAMP, updated_by = %s
            WHERE id = %s AND user_id = %s
            RETURNING id;
        """, [user_id, cart_item_id, user_id])
        
        if not cursor.fetchone():
            return {"message": "Cart item not found or already removed."}, status.HTTP_404_NOT_FOUND

    return {"message": "Item removed from cart successfully."}, status.HTTP_200_OK



def create_coupon(validated_data, user_id):
    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT id
            FROM public.coupons
            WHERE UPPER(code)=UPPER(%s)
            AND is_deleted=FALSE;
        """, [validated_data["code"]])

        if cursor.fetchone():
            return {
                "message": "Coupon code already exists."
            }, status.HTTP_400_BAD_REQUEST

        cursor.execute("""
            INSERT INTO public.coupons
            (
                code,
                discount_type,
                discount_value,
                maximum_discount_amount,
                minimum_order_amount,
                start_date,
                end_date,
                max_usage,
                max_usage_per_user,
                description,
                is_first_order_only,
                created_by,
                updated_by,
                is_active
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
            RETURNING id;
        """, [
            validated_data["code"],
            validated_data["discount_type"],
            validated_data["discount_value"],
            validated_data.get("maximum_discount_amount"),
            validated_data.get("minimum_order_amount", 0),
            validated_data["start_date"],
            validated_data["end_date"],
            validated_data.get("max_usage"),
            validated_data.get("max_usage_per_user", 1),
            validated_data.get("description"),
            validated_data.get("is_first_order_only", False),
            user_id,
            user_id,
            validated_data.get("is_active", True)
        ])

        coupon_id = cursor.fetchone()[0]

    return {
        "message": "Coupon created successfully.",
        "data": {
            "coupon_id": coupon_id
        }
    }, status.HTTP_201_CREATED




def get_coupons(user_id, coupon_id=None, coupon_code=None):

    sql = """
        SELECT
            id,
            code,
            discount_type,
            discount_value,
            maximum_discount_amount,
            minimum_order_amount,
            start_date,
            end_date,
            max_usage,
            used_count,
            max_usage_per_user,
            description,
            is_first_order_only,
            is_active,
            created_at
        FROM public.coupons
        WHERE is_deleted=FALSE
    """

    params = []

    if coupon_id:
        sql += " AND id=%s"
        params.append(coupon_id)

    if coupon_code:
        sql += " AND UPPER(code)=UPPER(%s)"
        params.append(coupon_code)

    sql += " ORDER BY created_at DESC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    data = []

    for row in rows:
        item = dict(zip(columns, row))

        item["discount_value"] = float(item["discount_value"])

        if item["maximum_discount_amount"] is not None:
            item["maximum_discount_amount"] = float(item["maximum_discount_amount"])

        if item["minimum_order_amount"] is not None:
            item["minimum_order_amount"] = float(item["minimum_order_amount"])

        data.append(item)

    if coupon_id or coupon_code:

        if not data:
            return {
                "message": "Coupon not found."
            }, status.HTTP_404_NOT_FOUND

        return {
            "message": "Coupon retrieved successfully.",
            "data": data[0]
        }, status.HTTP_200_OK

    return {
        "message": "Coupons retrieved successfully.",
        "data": data
    }, status.HTTP_200_OK




def update_coupon(validated_data, user_id):

    coupon_id = validated_data["id"]

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT id
            FROM public.coupons
            WHERE id=%s
            AND is_deleted=FALSE;
        """, [coupon_id])

        if not cursor.fetchone():
            return {
                "message": "Coupon not found."
            }, status.HTTP_404_NOT_FOUND

        cursor.execute("""
            SELECT id
            FROM public.coupons
            WHERE UPPER(code)=UPPER(%s)
            AND id<>%s
            AND is_deleted=FALSE;
        """, [
            validated_data["code"],
            coupon_id
        ])

        if cursor.fetchone():
            return {
                "message": "Coupon code already exists."
            }, status.HTTP_400_BAD_REQUEST

        cursor.execute("""
            UPDATE public.coupons
            SET
                code=%s,
                discount_type=%s,
                discount_value=%s,
                maximum_discount_amount=%s,
                minimum_order_amount=%s,
                start_date=%s,
                end_date=%s,
                max_usage=%s,
                max_usage_per_user=%s,
                description=%s,
                is_first_order_only=%s,
                is_active=%s,
                updated_at=CURRENT_TIMESTAMP,
                updated_by=%s
            WHERE id=%s;
        """, [
            validated_data["code"],
            validated_data["discount_type"],
            validated_data["discount_value"],
            validated_data.get("maximum_discount_amount"),
            validated_data.get("minimum_order_amount"),
            validated_data["start_date"],
            validated_data["end_date"],
            validated_data.get("max_usage"),
            validated_data.get("max_usage_per_user"),
            validated_data.get("description"),
            validated_data.get("is_first_order_only"),
            validated_data.get("is_active"),
            user_id,
            coupon_id
        ])

    return {
        "message": "Coupon updated successfully."
    }, status.HTTP_200_OK





def delete_coupon(coupon_id, user_id):

    if not coupon_id:
        return {
            "message": "Coupon id is required."
        }, status.HTTP_400_BAD_REQUEST

    with connection.cursor() as cursor:

        cursor.execute("""
            UPDATE public.coupons
            SET
                is_deleted=TRUE,
                is_active=FALSE,
                updated_at=CURRENT_TIMESTAMP,
                updated_by=%s
            WHERE id=%s
            RETURNING id;
        """, [
            user_id,
            coupon_id
        ])

        if not cursor.fetchone():
            return {
                "message": "Coupon not found."
            }, status.HTTP_404_NOT_FOUND

    return {
        "message": "Coupon deleted successfully."
    }, status.HTTP_200_OK


def get_order_listing(
    user_id,
    page=1,
    page_size=10,
    order_type=None
):

    page = max(int(page), 1)
    page_size = max(int(page_size), 1)
    offset = (page - 1) * page_size

    where_conditions = [
        "o.user_id = %s",
        "o.is_deleted = FALSE",
        "o.is_active = TRUE"
    ]

    params = [user_id]

    if order_type == "current":
        where_conditions.append("""
            o.order_status IN (
                'PLACED',
                'CONFIRMED',
                'PACKED',
                'SHIPPED',
                'OUT_FOR_DELIVERY'
            )
        """)

    elif order_type == "history":
        where_conditions.append("""
            o.order_status IN (
                'DELIVERED',
                'CANCELLED'
            )
        """)

    where_clause = " AND ".join(where_conditions)

    count_sql = f"""
        SELECT COUNT(*)
        FROM public.orders o
        WHERE {where_clause}
    """

    with connection.cursor() as cursor:
        cursor.execute(count_sql, params)
        total_records = cursor.fetchone()[0]

    if total_records == 0:
        return {
            "message": "Data not found.",
            "data": [],
            "pagination": {}
        }, status.HTTP_200_OK

    main_sql = f"""
        SELECT

            o.id,
            o.order_number,
            o.order_status,
            o.payment_status,
            o.payment_method,
            o.grand_total,
            o.ordered_at,
            o.tracking_id,
            o.courier_name,

            (
                SELECT COUNT(*)
                FROM public.order_items oi
                WHERE oi.order_id = o.id
                    AND oi.is_deleted = FALSE
                    AND oi.is_active = TRUE
            ) AS total_items,

            (
                SELECT COALESCE(
                    json_agg(
                        json_build_object(

                            'id', oi.id,

                            'product_id', oi.product_id,

                            'variant_id', oi.variant_id,

                            'product_name', oi.product_name,

                            'color', oi.color,

                            'size', oi.size,

                            'quantity', oi.quantity,

                            'mrp', oi.mrp,

                            'selling_price', oi.selling_price,

                            'total_amount', oi.total_amount,

                            'sku', pv.sku,

                            'image_url',
                            (
                                SELECT pvi.image_url
                                FROM public.product_variant_images pvi
                                WHERE
                                    pvi.variant_id = pv.id
                                    AND pvi.is_deleted = FALSE
                                    AND pvi.is_active = TRUE
                                ORDER BY pvi.display_order
                                LIMIT 1
                            )

                        )
                    ),
                    '[]'
                )
                FROM public.order_items oi

                INNER JOIN public.product_variants pv
                    ON pv.id = oi.variant_id

                WHERE
                    oi.order_id = o.id
                    AND oi.is_deleted = FALSE
                    AND oi.is_active = TRUE

            ) AS items

        FROM public.orders o

        WHERE {where_clause}

        ORDER BY o.ordered_at DESC

        LIMIT %s
        OFFSET %s
    """

    query_params = params + [page_size, offset]

    with connection.cursor() as cursor:

        cursor.execute(main_sql, query_params)

        rows = cursor.fetchall()

        columns = [col[0] for col in cursor.description]

    result = []

    for row in rows:

        item = dict(zip(columns, row))

        item["grand_total"] = float(item["grand_total"])

        if isinstance(item["items"], str):
            item["items"] = json.loads(item["items"])

        for product in item["items"]:

            product["mrp"] = float(product["mrp"])
            product["selling_price"] = float(product["selling_price"])
            product["total_amount"] = float(product["total_amount"])

        result.append(item)

    pagination = {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": math.ceil(total_records / page_size),
        "has_next": page * page_size < total_records,
        "has_previous": page > 1
    }

    return {
        "message": "Data fetched successfully.",
        "data": result,
        "pagination": pagination
    }, status.HTTP_200_OK



def get_order_detail(user_id, order_id):

    order_sql = """
        SELECT
            o.id,
            o.order_number,

            o.customer_name,
            o.customer_email,
            o.customer_mobile,

            o.address_line_1,
            o.address_line_2,
            o.landmark,
            o.city,
            o.state,
            o.country,
            o.pincode,

            o.payment_method,
            o.payment_status,
            o.order_status,

            o.tracking_id,
            o.courier_name,

            o.subtotal,
            o.discount_amount,
            o.shipping_amount,
            o.tax_amount,
            o.grand_total,

            o.ordered_at,
            o.shipped_at,
            o.delivered_at,
            o.cancelled_at

        FROM public.orders o

        WHERE
            o.id=%s
            AND o.user_id=%s
            AND o.is_deleted=FALSE
            AND o.is_active=TRUE

        LIMIT 1
    """

    with connection.cursor() as cursor:
        cursor.execute(order_sql, [order_id, user_id])

        row = cursor.fetchone()

        if not row:
            return {
                "message": "Order not found."
            }, status.HTTP_404_NOT_FOUND

        columns = [col[0] for col in cursor.description]
        order = dict(zip(columns, row))

    items_sql = """
        SELECT

            oi.id,

            oi.product_id,
            oi.variant_id,

            oi.product_name,

            oi.color,
            oi.size,

            oi.quantity,

            oi.mrp,
            oi.selling_price,
            oi.total_amount,

            pv.sku,

            (
                SELECT pvi.image_url
                FROM public.product_variant_images pvi
                WHERE
                    pvi.variant_id = pv.id
                    AND pvi.is_deleted = FALSE
                    AND pvi.is_active = TRUE
                ORDER BY pvi.display_order
                LIMIT 1
            ) AS image_url

        FROM public.order_items oi

        INNER JOIN public.product_variants pv
            ON pv.id = oi.variant_id

        WHERE
            oi.order_id = %s
            AND oi.is_deleted = FALSE
            AND oi.is_active = TRUE

        ORDER BY oi.id
    """

    with connection.cursor() as cursor:

        cursor.execute(items_sql, [order_id])

        rows = cursor.fetchall()

        columns = [col[0] for col in cursor.description]

    items = []

    for row in rows:

        item = dict(zip(columns, row))

        item["mrp"] = float(item["mrp"] or 0)
        item["selling_price"] = float(item["selling_price"] or 0)
        item["total_amount"] = float(item["total_amount"] or 0)

        items.append(item)

    order["subtotal"] = float(order["subtotal"] or 0)
    order["discount_amount"] = float(order["discount_amount"] or 0)
    order["shipping_amount"] = float(order["shipping_amount"] or 0)
    order["tax_amount"] = float(order["tax_amount"] or 0)
    order["grand_total"] = float(order["grand_total"] or 0)

    response = {

        "id": order["id"],

        "order_number": order["order_number"],

        "order_status": order["order_status"],

        "payment_status": order["payment_status"],

        "payment_method": order["payment_method"],

        "ordered_at": order["ordered_at"],

        "shipped_at": order["shipped_at"],

        "delivered_at": order["delivered_at"],

        "cancelled_at": order["cancelled_at"],

        "tracking_id": order["tracking_id"],

        "courier_name": order["courier_name"],

        "address": {

            "customer_name": order["customer_name"],

            "customer_email": order["customer_email"],

            "customer_mobile": order["customer_mobile"],

            "address_line_1": order["address_line_1"],

            "address_line_2": order["address_line_2"],

            "landmark": order["landmark"],

            "city": order["city"],

            "state": order["state"],

            "country": order["country"],

            "pincode": order["pincode"]

        },

        "price_summary": {

            "subtotal": order["subtotal"],

            "discount_amount": order["discount_amount"],

            "shipping_amount": order["shipping_amount"],

            "tax_amount": order["tax_amount"],

            "grand_total": order["grand_total"]

        },

        "items": items

    }

    return {

        "message": "Data fetched successfully.",

        "data": response

    }, status.HTTP_200_OK



@transaction.atomic
def create_product(data, user_id):

    category_id = data.get("category_id")
    sub_category_id = data.get("sub_category_id")

    name = data.get("name").strip()
    description = data.get("description")
    fabric = data.get("fabric")
    gsm = data.get("gsm")

    is_featured = data.get("is_featured", False)
    is_new_arrival = data.get("is_new_arrival", False)
    is_active = data.get("is_active", True)

    key_highlights = json.dumps(
        data.get("key_highlights", {})
    )

    tags = data.get("tags", [])
    variants = data.get("variants", [])

    with connection.cursor() as cursor:

            # --------------------------------------------------
            # Product Name Validation
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT 1
                FROM products
                WHERE LOWER(name)=LOWER(%s)
                AND is_deleted=FALSE
                """,
                [name]
            )

            if cursor.fetchone():
                return {
                    "message": "Product already exists.",
                    "data": {}
                }, status.HTTP_400_BAD_REQUEST

            # --------------------------------------------------
            # Category Validation
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT 1
                FROM categories
                WHERE id=%s
                AND is_deleted=FALSE
                AND is_active=TRUE
                """,
                [category_id]
            )

            if not cursor.fetchone():
                return {
                    "message": "Category not found.",
                    "data": {}
                }, status.HTTP_404_NOT_FOUND

            # --------------------------------------------------
            # Sub Category Validation
            # --------------------------------------------------

            if sub_category_id:

                cursor.execute(
                    """
                    SELECT 1
                    FROM sub_categories
                    WHERE id=%s
                    AND category_id=%s
                    AND is_deleted=FALSE
                    AND is_active=TRUE
                    """,
                    [
                        sub_category_id,
                        category_id
                    ]
                )

                if not cursor.fetchone():
                    return {
                        "message": "Sub category not found.",
                        "data": {}
                    }, status.HTTP_404_NOT_FOUND

            # --------------------------------------------------
            # Tag Validation
            # --------------------------------------------------

            if tags:

                cursor.execute(
                    """
                    SELECT id
                    FROM product_tags
                    WHERE id = ANY(%s)
                    AND is_deleted = FALSE
                    AND is_active = TRUE
                    """,
                    [tags]
                )

                existing_tags = {
                    row[0]
                    for row in cursor.fetchall()
                }

                invalid_tags = [
                    tag
                    for tag in tags
                    if tag not in existing_tags
                ]

                if invalid_tags:
                    return {
                        "message": "Invalid tag ids.",
                        "data": {
                            "invalid_tag_ids": invalid_tags
                        }
                    }, status.HTTP_400_BAD_REQUEST

            # --------------------------------------------------
            # SKU Validation
            # --------------------------------------------------

            sku_list = [
                variant["sku"]
                for variant in variants
            ]

            if sku_list:

                cursor.execute(
                    """
                    SELECT sku
                    FROM product_variants
                    WHERE sku = ANY(%s)
                    AND is_deleted = FALSE
                    """,
                    [sku_list]
                )

                existing_skus = [
                    row[0]
                    for row in cursor.fetchall()
                ]

                if existing_skus:
                    return {
                        "message": "SKU already exists.",
                        "data": {
                            "existing_skus": existing_skus
                        }
                    }, status.HTTP_400_BAD_REQUEST

            # --------------------------------------------------
            # Insert Product
            # --------------------------------------------------

            cursor.execute(
                """
                INSERT INTO products
                (
                    category_id,
                    sub_category_id,
                    name,
                    description,
                    fabric,
                    gsm,
                    is_featured,
                    is_new_arrival,
                    key_highlights,
                    is_active,
                    created_by,
                    updated_by,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW(),
                    NOW()
                )
                RETURNING id
                """,
                [
                    category_id,
                    sub_category_id,
                    name,
                    description,
                    fabric,
                    gsm,
                    is_featured,
                    is_new_arrival,
                    key_highlights,
                    is_active,
                    user_id,
                    user_id
                ]
            )

            product_id = cursor.fetchone()[0]

                        # --------------------------------------------------
            # Insert Product Tags
            # --------------------------------------------------

            if tags:

                cursor.executemany(
                    """
                    INSERT INTO product_tag_mapping
                    (
                        product_id,
                        tag_id,
                        created_by,
                        updated_by,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        NOW(),
                        NOW()
                    )
                    """,
                    [
                        (
                            product_id,
                            tag_id,
                            user_id,
                            user_id
                        )
                        for tag_id in tags
                    ]
                )
            
                        # --------------------------------------------------
            # Insert Product Variants
            # --------------------------------------------------

            for variant in variants:

                cursor.execute(
                    """
                    INSERT INTO product_variants
                    (
                        product_id,
                        sku,
                        color,
                        mrp,
                        selling_price,
                        cost_price,
                        is_default,
                        is_active,
                        created_by,
                        updated_by,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        NOW(),
                        NOW()
                    )
                    RETURNING id
                    """,
                    [
                        product_id,
                        variant["sku"],
                        variant["color"],
                        variant["mrp"],
                        variant["selling_price"],
                        variant.get("cost_price"),
                        variant["is_default"],
                        variant["is_active"],
                        user_id,
                        user_id
                    ]
                )

                variant_id = cursor.fetchone()[0]


                sizes = variant.get("sizes", [])

                if sizes:

                    cursor.executemany(
                        """
                        INSERT INTO product_variant_sizes
                        (
                            variant_id,
                            size,
                            stock_quantity,
                            is_active,
                            created_by,
                            updated_by,
                            created_at,
                            updated_at
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            NOW(),
                            NOW()
                        )
                        """,
                        [
                            (
                                variant_id,
                                size["size"],
                                size["stock_quantity"],
                                size["is_active"],
                                user_id,
                                user_id
                            )
                            for size in sizes
                        ]
                    )

    product_data, _ = get_product_detail(
        product_id=product_id
    )

    return {
        "message": "Product created successfully.",
        "data": product_data.get("data")
    }, status.HTTP_201_CREATED


# def create_product(data, user_id):

#     category_id = data.get("category_id")
#     sub_category_id = data.get("sub_category_id")

#     name = data.get("name").strip()
#     description = data.get("description")
#     fabric = data.get("fabric")
#     gsm = data.get("gsm")

#     is_featured = data.get("is_featured", False)
#     is_new_arrival = data.get("is_new_arrival", False)
#     is_active = data.get("is_active", True)

#     key_highlights = json.dumps(
#         data.get("key_highlights", {})
#     )

#     tags = data.get("tags", [])
#     variants = data.get("variants", [])

#     with connection.cursor() as cursor:

#         try:

#             # --------------------------------------------------
#             # Product Name Validation
#             # --------------------------------------------------

#             cursor.execute(
#                 """
#                 SELECT 1
#                 FROM products
#                 WHERE LOWER(name)=LOWER(%s)
#                 AND is_deleted=FALSE
#                 """,
#                 [name]
#             )

#             if cursor.fetchone():
#                 return {
#                     "message": "Product already exists.",
#                     "data": {}
#                 }, status.HTTP_400_BAD_REQUEST

#             # --------------------------------------------------
#             # Category Validation
#             # --------------------------------------------------

#             cursor.execute(
#                 """
#                 SELECT 1
#                 FROM categories
#                 WHERE id=%s
#                 AND is_deleted=FALSE
#                 AND is_active=TRUE
#                 """,
#                 [category_id]
#             )

#             if not cursor.fetchone():
#                 return {
#                     "message": "Category not found.",
#                     "data": {}
#                 }, status.HTTP_404_NOT_FOUND

#             # --------------------------------------------------
#             # Sub Category Validation
#             # --------------------------------------------------

#             if sub_category_id:

#                 cursor.execute(
#                     """
#                     SELECT 1
#                     FROM sub_categories
#                     WHERE id=%s
#                     AND category_id=%s
#                     AND is_deleted=FALSE
#                     AND is_active=TRUE
#                     """,
#                     [
#                         sub_category_id,
#                         category_id
#                     ]
#                 )

#                 if not cursor.fetchone():
#                     return {
#                         "message": "Sub category not found.",
#                         "data": {}
#                     }, status.HTTP_404_NOT_FOUND

#             # --------------------------------------------------
#             # Tag Validation
#             # --------------------------------------------------

#             if tags:

#                 cursor.execute(
#                     """
#                     SELECT id
#                     FROM product_tags
#                     WHERE id = ANY(%s)
#                     AND is_deleted = FALSE
#                     AND is_active = TRUE
#                     """,
#                     [tags]
#                 )

#                 existing_tags = {
#                     row[0]
#                     for row in cursor.fetchall()
#                 }

#                 invalid_tags = [
#                     tag
#                     for tag in tags
#                     if tag not in existing_tags
#                 ]

#                 if invalid_tags:
#                     return {
#                         "message": "Invalid tag ids.",
#                         "data": {
#                             "invalid_tag_ids": invalid_tags
#                         }
#                     }, status.HTTP_400_BAD_REQUEST

#             # --------------------------------------------------
#             # SKU Validation
#             # --------------------------------------------------

#             sku_list = [
#                 variant["sku"]
#                 for variant in variants
#             ]

#             if sku_list:

#                 cursor.execute(
#                     """
#                     SELECT sku
#                     FROM product_variants
#                     WHERE sku = ANY(%s)
#                     AND is_deleted = FALSE
#                     """,
#                     [sku_list]
#                 )

#                 existing_skus = [
#                     row[0]
#                     for row in cursor.fetchall()
#                 ]

#                 if existing_skus:
#                     return {
#                         "message": "SKU already exists.",
#                         "data": {
#                             "existing_skus": existing_skus
#                         }
#                     }, status.HTTP_400_BAD_REQUEST

#             # --------------------------------------------------
#             # Insert Product
#             # --------------------------------------------------

#             cursor.execute(
#                 """
#                 INSERT INTO products
#                 (
#                     category_id,
#                     sub_category_id,
#                     name,
#                     description,
#                     fabric,
#                     gsm,
#                     is_featured,
#                     is_new_arrival,
#                     key_highlights,
#                     is_active,
#                     created_by,
#                     updated_by,
#                     created_at,
#                     updated_at
#                 )
#                 VALUES
#                 (
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     %s,
#                     NOW(),
#                     NOW()
#                 )
#                 RETURNING id
#                 """,
#                 [
#                     category_id,
#                     sub_category_id,
#                     name,
#                     description,
#                     fabric,
#                     gsm,
#                     is_featured,
#                     is_new_arrival,
#                     key_highlights,
#                     is_active,
#                     user_id,
#                     user_id
#                 ]
#             )

#             product_id = cursor.fetchone()[0]

#                         # --------------------------------------------------
#             # Insert Product Tags
#             # --------------------------------------------------

#             if tags:

#                 cursor.executemany(
#                     """
#                     INSERT INTO product_tag_mapping
#                     (
#                         product_id,
#                         tag_id,
#                         created_by,
#                         updated_by,
#                         created_at,
#                         updated_at
#                     )
#                     VALUES
#                     (
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         NOW(),
#                         NOW()
#                     )
#                     """,
#                     [
#                         (
#                             product_id,
#                             tag_id,
#                             user_id,
#                             user_id
#                         )
#                         for tag_id in tags
#                     ]
#                 )
            
#                         # --------------------------------------------------
#             # Insert Product Variants
#             # --------------------------------------------------

#             for variant in variants:

#                 cursor.execute(
#                     """
#                     INSERT INTO product_variants
#                     (
#                         product_id,
#                         sku,
#                         color,
#                         mrp,
#                         selling_price,
#                         cost_price,
#                         is_default,
#                         is_active,
#                         created_by,
#                         updated_by,
#                         created_at,
#                         updated_at
#                     )
#                     VALUES
#                     (
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         %s,
#                         NOW(),
#                         NOW()
#                     )
#                     RETURNING id
#                     """,
#                     [
#                         product_id,
#                         variant["sku"],
#                         variant["color"],
#                         variant["mrp"],
#                         variant["selling_price"],
#                         variant.get("cost_price"),
#                         variant["is_default"],
#                         variant["is_active"],
#                         user_id,
#                         user_id
#                     ]
#                 )

#                 variant_id = cursor.fetchone()[0]


#                 sizes = variant.get("sizes", [])

#                 if sizes:

#                     cursor.executemany(
#                         """
#                         INSERT INTO product_variant_sizes
#                         (
#                             variant_id,
#                             size,
#                             stock_quantity,
#                             is_active,
#                             created_by,
#                             updated_by,
#                             created_at,
#                             updated_at
#                         )
#                         VALUES
#                         (
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             %s,
#                             NOW(),
#                             NOW()
#                         )
#                         """,
#                         [
#                             (
#                                 variant_id,
#                                 size["size"],
#                                 size["stock_quantity"],
#                                 size["is_active"],
#                                 user_id,
#                                 user_id
#                             )
#                             for size in sizes
#                         ]
#                     )

#             connection.commit()

#         except Exception:
#             connection.rollback()
#             raise

#     product_data, _ = get_product_detail(
#         product_id=product_id
#     )

#     return {
#         "message": "Product created successfully.",
#         "data": product_data.get("data")
#     }, status.HTTP_201_CREATED


def update_product(data, user_id):

    product_id = data.get("id")

    category_id = data.get("category_id")
    sub_category_id = data.get("sub_category_id")

    name = data.get("name").strip()
    description = data.get("description")
    fabric = data.get("fabric")
    gsm = data.get("gsm")

    is_featured = data.get("is_featured", False)
    is_new_arrival = data.get("is_new_arrival", False)
    is_active = data.get("is_active", True)

    key_highlights = json.dumps(
        data.get("key_highlights", {})
    )

    tags = data.get("tags", [])
    variants = data.get("variants", [])

    delete_tag_ids = data.get("delete_tag_ids", [])
    delete_variant_ids = data.get("delete_variant_ids", [])
    delete_size_ids = data.get("delete_size_ids", [])

    with connection.cursor() as cursor:

        try:

            cursor.execute(
                """
                SELECT 1
                FROM products
                WHERE id=%s
                AND is_deleted=FALSE
                """,
                [product_id]
            )

            if not cursor.fetchone():
                return {
                    "message": "Product not found.",
                    "data": {}
                }, status.HTTP_404_NOT_FOUND


            cursor.execute(
                """
                SELECT 1
                FROM products
                WHERE LOWER(name)=LOWER(%s)
                AND id<>%s
                AND is_deleted=FALSE
                """,
                [name, product_id]
            )

            if cursor.fetchone():
                return {
                    "message": "Product already exists.",
                    "data": {}
                }, status.HTTP_400_BAD_REQUEST

            # --------------------------------------------------
            # Category Validation
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT 1
                FROM categories
                WHERE id=%s
                AND is_deleted=FALSE
                AND is_active=TRUE
                """,
                [category_id]
            )

            if not cursor.fetchone():
                return {
                    "message": "Category not found.",
                    "data": {}
                }, status.HTTP_404_NOT_FOUND

            # --------------------------------------------------
            # Sub Category Validation
            # --------------------------------------------------

            if sub_category_id:

                cursor.execute(
                    """
                    SELECT 1
                    FROM sub_categories
                    WHERE id=%s
                    AND category_id=%s
                    AND is_deleted=FALSE
                    AND is_active=TRUE
                    """,
                    [
                        sub_category_id,
                        category_id
                    ]
                )

                if not cursor.fetchone():
                    return {
                        "message": "Sub category not found.",
                        "data": {}
                    }, status.HTTP_404_NOT_FOUND

            # --------------------------------------------------
            # Tag Validation
            # --------------------------------------------------

            if tags:

                cursor.execute(
                    """
                    SELECT id
                    FROM product_tags
                    WHERE id = ANY(%s)
                    AND is_deleted = FALSE
                    AND is_active = TRUE
                    """,
                    [tags]
                )

                existing_tags = {
                    row[0]
                    for row in cursor.fetchall()
                }

                invalid_tags = [
                    tag
                    for tag in tags
                    if tag not in existing_tags
                ]

                if invalid_tags:
                    return {
                        "message": "Invalid tag ids.",
                        "data": {
                            "invalid_tag_ids": invalid_tags
                        }
                    }, status.HTTP_400_BAD_REQUEST

            # --------------------------------------------------
            # Variant Ownership Validation
            # --------------------------------------------------

            update_variant_ids = [
                variant["id"]
                for variant in variants
                if variant.get("id")
            ]

            if update_variant_ids:

                cursor.execute(
                    """
                    SELECT id
                    FROM product_variants
                    WHERE id = ANY(%s)
                    AND product_id = %s
                    AND is_deleted = FALSE
                    """,
                    [update_variant_ids, product_id]
                )

                owned_variant_ids = {
                    row[0]
                    for row in cursor.fetchall()
                }

                invalid_variant_ids = [
                    variant_id
                    for variant_id in update_variant_ids
                    if variant_id not in owned_variant_ids
                ]

                if invalid_variant_ids:
                    return {
                        "message": "Invalid variant ids.",
                        "data": {
                            "invalid_variant_ids": invalid_variant_ids
                        }
                    }, status.HTTP_400_BAD_REQUEST

            if delete_variant_ids:

                cursor.execute(
                    """
                    SELECT id
                    FROM product_variants
                    WHERE id = ANY(%s)
                    AND product_id = %s
                    AND is_deleted = FALSE
                    """,
                    [delete_variant_ids, product_id]
                )

                owned_delete_variant_ids = {
                    row[0]
                    for row in cursor.fetchall()
                }

                invalid_delete_variant_ids = [
                    variant_id
                    for variant_id in delete_variant_ids
                    if variant_id not in owned_delete_variant_ids
                ]

                if invalid_delete_variant_ids:
                    return {
                        "message": "Invalid delete variant ids.",
                        "data": {
                            "invalid_variant_ids": invalid_delete_variant_ids
                        }
                    }, status.HTTP_400_BAD_REQUEST
            

            if delete_size_ids:

                cursor.execute("""
                    SELECT pvs.id
                    FROM product_variant_sizes pvs
                    JOIN product_variants pv
                        ON pv.id = pvs.variant_id
                    WHERE pvs.id = ANY(%s)
                    AND pv.product_id = %s
                    AND pvs.is_deleted = FALSE
                    AND pv.is_deleted = FALSE
                """, [delete_size_ids, product_id])

                existing_size_ids = {
                    row[0]
                    for row in cursor.fetchall()
                }

                invalid_size_ids = [
                    size_id
                    for size_id in delete_size_ids
                    if size_id not in existing_size_ids
                ]

                if invalid_size_ids:
                    return {
                        "message": "Invalid delete size ids.",
                        "data": {
                            "invalid_size_ids": invalid_size_ids
                        }
                    }, status.HTTP_400_BAD_REQUEST
            # --------------------------------------------------
            # SKU Validation
            # --------------------------------------------------

            if delete_size_ids:

                cursor.execute("""
                    UPDATE product_variant_sizes
                    SET
                        is_deleted = TRUE,
                        is_active = FALSE,
                        updated_by = %s,
                        updated_at = NOW()
                    WHERE id = ANY(%s)
                    AND is_deleted = FALSE
                """, [
                    user_id,
                    delete_size_ids
                ])


            sku_list = [
                variant["sku"]
                for variant in variants
            ]

            if sku_list:

                cursor.execute(
                    """
                    SELECT sku
                    FROM product_variants
                    WHERE sku = ANY(%s)
                    AND is_deleted = FALSE
                    AND NOT (
                        product_id = %s
                        AND id = ANY(%s)
                    )
                    """,
                    [
                        sku_list,
                        product_id,
                        update_variant_ids or [0]
                    ]
                )

                existing_skus = [
                    row[0]
                    for row in cursor.fetchall()
                ]

                if existing_skus:
                    return {
                        "message": "SKU already exists.",
                        "data": {
                            "existing_skus": existing_skus
                        }
                    }, status.HTTP_400_BAD_REQUEST

            # --------------------------------------------------
            # Update Product
            # --------------------------------------------------

            cursor.execute(
                """
                UPDATE products
                SET
                    category_id=%s,
                    sub_category_id=%s,
                    name=%s,
                    description=%s,
                    fabric=%s,
                    gsm=%s,
                    is_featured=%s,
                    is_new_arrival=%s,
                    key_highlights=%s,
                    is_active=%s,
                    updated_by=%s,
                    updated_at=NOW()
                WHERE id=%s
                AND is_deleted=FALSE
                """,
                [
                    category_id,
                    sub_category_id,
                    name,
                    description,
                    fabric,
                    gsm,
                    is_featured,
                    is_new_arrival,
                    key_highlights,
                    is_active,
                    user_id,
                    product_id
                ]
            )

            # --------------------------------------------------
            # Soft Delete Tags
            # --------------------------------------------------

            if delete_tag_ids:

                cursor.execute(
                    """
                    UPDATE product_tag_mapping
                    SET
                        is_deleted=TRUE,
                        is_active=FALSE,
                        updated_by=%s,
                        updated_at=NOW()
                    WHERE product_id=%s
                    AND tag_id = ANY(%s)
                    AND is_deleted=FALSE
                    """,
                    [
                        user_id,
                        product_id,
                        delete_tag_ids
                    ]
                )

            # --------------------------------------------------
            # Insert Product Tags
            # --------------------------------------------------

            if tags:

                cursor.execute(
                    """
                    SELECT tag_id
                    FROM product_tag_mapping
                    WHERE product_id=%s
                    AND tag_id = ANY(%s)
                    AND is_deleted=FALSE
                    """,
                    [product_id, tags]
                )

                existing_mapped_tags = {
                    row[0]
                    for row in cursor.fetchall()
                }

                new_tags = [
                    tag_id
                    for tag_id in tags
                    if tag_id not in existing_mapped_tags
                ]

                if new_tags:

                    cursor.executemany(
                        """
                        INSERT INTO product_tag_mapping
                        (
                            product_id,
                            tag_id,
                            created_by,
                            updated_by,
                            created_at,
                            updated_at
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            NOW(),
                            NOW()
                        )
                        """,
                        [
                            (
                                product_id,
                                tag_id,
                                user_id,
                                user_id
                            )
                            for tag_id in new_tags
                        ]
                    )

            # --------------------------------------------------
            # Soft Delete Variants
            # --------------------------------------------------

            if delete_variant_ids:

                cursor.execute(
                    """
                    UPDATE product_variants
                    SET
                        is_deleted=TRUE,
                        is_active=FALSE,
                        is_default=FALSE,
                        updated_by=%s,
                        updated_at=NOW()
                    WHERE product_id=%s
                    AND id = ANY(%s)
                    AND is_deleted=FALSE
                    """,
                    [
                        user_id,
                        product_id,
                        delete_variant_ids
                    ]
                )

                cursor.execute(
                    """
                    UPDATE product_variant_sizes
                    SET
                        is_deleted=TRUE,
                        is_active=FALSE,
                        updated_by=%s,
                        updated_at=NOW()
                    WHERE variant_id = ANY(%s)
                    AND is_deleted=FALSE
                    """,
                    [
                        user_id,
                        delete_variant_ids
                    ]
                )

            # --------------------------------------------------
            # Reset Default Variants
            # --------------------------------------------------

            cursor.execute(
                """
                UPDATE product_variants
                SET
                    is_default=FALSE,
                    updated_by=%s,
                    updated_at=NOW()
                WHERE product_id=%s
                AND is_deleted=FALSE
                """,
                [user_id, product_id]
            )

            # --------------------------------------------------
            # Upsert Product Variants
            # --------------------------------------------------

            restocked_size_ids = []

            for variant in variants:

                variant_id = variant.get("id")

                if variant_id:

                    cursor.execute(
                        """
                        UPDATE product_variants
                        SET
                            sku=%s,
                            color=%s,
                            mrp=%s,
                            selling_price=%s,
                            cost_price=%s,
                            is_default=%s,
                            is_active=%s,
                            updated_by=%s,
                            updated_at=NOW()
                        WHERE id=%s
                        AND product_id=%s
                        AND is_deleted=FALSE
                        """,
                        [
                            variant["sku"],
                            variant["color"],
                            variant["mrp"],
                            variant["selling_price"],
                            variant.get("cost_price"),
                            variant["is_default"],
                            variant.get("is_active", True),
                            user_id,
                            variant_id,
                            product_id
                        ]
                    )

                else:

                    cursor.execute(
                        """
                        INSERT INTO product_variants
                        (
                            product_id,
                            sku,
                            color,
                            mrp,
                            selling_price,
                            cost_price,
                            is_default,
                            is_active,
                            created_by,
                            updated_by,
                            created_at,
                            updated_at
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            NOW(),
                            NOW()
                        )
                        RETURNING id
                        """,
                        [
                            product_id,
                            variant["sku"],
                            variant["color"],
                            variant["mrp"],
                            variant["selling_price"],
                            variant.get("cost_price"),
                            variant["is_default"],
                            variant.get("is_active", True),
                            user_id,
                            user_id
                        ]
                    )

                    variant_id = cursor.fetchone()[0]

                sizes = variant.get("sizes", [])

                update_size_ids = [
                    size["id"]
                    for size in sizes
                    if size.get("id")
                ]

                if update_size_ids:

                    cursor.execute(
                        """
                        SELECT id
                        FROM product_variant_sizes
                        WHERE id = ANY(%s)
                        AND variant_id = %s
                        AND is_deleted = FALSE
                        """,
                        [update_size_ids, variant_id]
                    )

                    owned_size_ids = {
                        row[0]
                        for row in cursor.fetchall()
                    }

                    invalid_size_ids = [
                        size_id
                        for size_id in update_size_ids
                        if size_id not in owned_size_ids
                    ]

                    if invalid_size_ids:
                        connection.rollback()
                        return {
                            "message": "Invalid size ids.",
                            "data": {
                                "invalid_size_ids": invalid_size_ids
                            }
                        }, status.HTTP_400_BAD_REQUEST

                for size in sizes:

                    size_id = size.get("id")

                    if size_id:

                        cursor.execute(
                            """
                            SELECT stock_quantity
                            FROM product_variant_sizes
                            WHERE id=%s
                            AND variant_id=%s
                            AND is_deleted=FALSE
                            """,
                            [size_id, variant_id]
                        )

                        previous_row = cursor.fetchone()
                        previous_stock = previous_row[0] if previous_row else 0

                        cursor.execute(
                            """
                            UPDATE product_variant_sizes
                            SET
                                size=%s,
                                stock_quantity=%s,
                                is_active=%s,
                                updated_by=%s,
                                updated_at=NOW()
                            WHERE id=%s
                            AND variant_id=%s
                            AND is_deleted=FALSE
                            """,
                            [
                                size["size"],
                                size["stock_quantity"],
                                size.get("is_active", True),
                                user_id,
                                size_id,
                                variant_id
                            ]
                        )

                        if (
                            (not previous_stock or previous_stock <= 0)
                            and size["stock_quantity"] > 0
                        ):
                            restocked_size_ids.append(size_id)

                    else:

                        cursor.execute(
                            """
                            INSERT INTO product_variant_sizes
                            (
                                variant_id,
                                size,
                                stock_quantity,
                                is_active,
                                created_by,
                                updated_by,
                                created_at,
                                updated_at
                            )
                            VALUES
                            (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                NOW(),
                                NOW()
                            )
                            """,
                            [
                                variant_id,
                                size["size"],
                                size["stock_quantity"],
                                size.get("is_active", True),
                                user_id,
                                user_id
                            ]
                        )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

    for size_id in restocked_size_ids:
        notify_users_for_restock(size_id)

    product_data, _ = get_product_detail(
        product_id=product_id
    )

    return {
        "message": "Product updated successfully.",
        "data": product_data.get("data")
    }, status.HTTP_200_OK


def delete_product(product_id, user_id):

    if not product_id:
        return {
            "message": "Product id is required.",
            "data": {}
        }, status.HTTP_400_BAD_REQUEST

    with connection.cursor() as cursor:

        try:

            # --------------------------------------------------
            # Product Existence Validation
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT 1
                FROM products
                WHERE id=%s
                AND is_deleted=FALSE
                """,
                [product_id]
            )

            if not cursor.fetchone():
                return {
                    "message": "Product not found.",
                    "data": {}
                }, status.HTTP_404_NOT_FOUND

            # --------------------------------------------------
            # Soft Delete Product
            # --------------------------------------------------

            cursor.execute(
                """
                UPDATE products
                SET
                    is_deleted=TRUE,
                    is_active=FALSE,
                    updated_by=%s,
                    updated_at=NOW()
                WHERE id=%s
                AND is_deleted=FALSE
                """,
                [user_id, product_id]
            )

            # --------------------------------------------------
            # Soft Delete Tag Mappings
            # --------------------------------------------------

            cursor.execute(
                """
                UPDATE product_tag_mapping
                SET
                    is_deleted=TRUE,
                    is_active=FALSE,
                    updated_by=%s,
                    updated_at=NOW()
                WHERE product_id=%s
                AND is_deleted=FALSE
                """,
                [user_id, product_id]
            )

            # --------------------------------------------------
            # Soft Delete Variants
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM product_variants
                WHERE product_id=%s
                AND is_deleted=FALSE
                """,
                [product_id]
            )

            variant_ids = [
                row[0]
                for row in cursor.fetchall()
            ]

            if variant_ids:

                cursor.execute(
                    """
                    UPDATE product_variants
                    SET
                        is_deleted=TRUE,
                        is_active=FALSE,
                        is_default=FALSE,
                        updated_by=%s,
                        updated_at=NOW()
                    WHERE product_id=%s
                    AND is_deleted=FALSE
                    """,
                    [user_id, product_id]
                )

                # --------------------------------------------------
                # Soft Delete Variant Sizes
                # --------------------------------------------------

                cursor.execute(
                    """
                    UPDATE product_variant_sizes
                    SET
                        is_deleted=TRUE,
                        is_active=FALSE,
                        updated_by=%s,
                        updated_at=NOW()
                    WHERE variant_id = ANY(%s)
                    AND is_deleted=FALSE
                    """,
                    [user_id, variant_ids]
                )

                # --------------------------------------------------
                # Soft Delete Variant Images
                # --------------------------------------------------

                cursor.execute(
                    """
                    UPDATE product_variant_images
                    SET
                        is_deleted=TRUE,
                        is_active=FALSE,
                        updated_by=%s,
                        updated_at=NOW()
                    WHERE variant_id = ANY(%s)
                    AND is_deleted=FALSE
                    """,
                    [user_id, variant_ids]
                )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

    return {
        "message": "Product deleted successfully.",
        "data": {}
    }, status.HTTP_200_OK



ADDRESS_COLUMNS = [
    "id",
    "user_id",
    "full_name",
    "mobile",
    "address_line_1",
    "address_line_2",
    "landmark",
    "city",
    "state",
    "country",
    "pincode",
    "address_type",
    "is_default",
    "created_at",
    "updated_at"
]


def create_address(data, user_id):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM addresses
            WHERE user_id = %s
            AND is_deleted = FALSE
            """,
            [user_id]
        )

        is_first_address = cursor.fetchone()[0] == 0

        is_default = is_first_address or data.get("is_default", False)

        if is_default:
            cursor.execute(
                """
                UPDATE addresses
                SET is_default = FALSE
                WHERE user_id = %s
                AND is_deleted = FALSE
                AND is_default = TRUE
                """,
                [user_id]
            )

        cursor.execute(
            """
            INSERT INTO addresses
            (
                user_id,
                full_name,
                mobile,
                address_line_1,
                address_line_2,
                landmark,
                city,
                state,
                country,
                pincode,
                address_type,
                is_default,
                created_by,
                updated_by,
                created_at,
                updated_at
            )
            VALUES
            (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
            RETURNING id
            """,
            [
                user_id,
                data.get("full_name"),
                data.get("mobile"),
                data.get("address_line_1"),
                data.get("address_line_2"),
                data.get("landmark"),
                data.get("city"),
                data.get("state"),
                data.get("country", "India"),
                data.get("pincode"),
                data.get("address_type", "Home"),
                is_default,
                user_id,
                user_id
            ]
        )

        address_id = cursor.fetchone()[0]

        connection.commit()

    address_data, _ = get_addresses(
        user_id=user_id,
        address_id=address_id
    )

    return {
        "message": "Address created successfully.",
        "data": address_data.get("data")
    }, status.HTTP_201_CREATED



def get_addresses(user_id, address_id=None):

    columns_str = ", ".join(ADDRESS_COLUMNS)

    params = [user_id]

    where_clause = """
        WHERE user_id = %s
        AND is_deleted = FALSE
    """

    if address_id:
        where_clause += " AND id = %s"
        params.append(address_id)

    sql = f"""
        SELECT {columns_str}
        FROM addresses
        {where_clause}
        ORDER BY is_default DESC, created_at DESC
    """

    with connection.cursor() as cursor:

        cursor.execute(sql, params)

        rows = cursor.fetchall()

        if not rows:
            return {
                "message": "Address not found." if address_id else "Data not found.",
                "data": [] if not address_id else {}
            }, (
                status.HTTP_404_NOT_FOUND
                if address_id
                else status.HTTP_200_OK
            )

        result = db_query_result_to_json(rows, ADDRESS_COLUMNS)

        if address_id:
            return {
                "message": "Data fetched successfully.",
                "data": result[0]
            }, status.HTTP_200_OK

        return {
            "message": "Data fetched successfully.",
            "data": result
        }, status.HTTP_200_OK



def update_address(data, user_id):

    address_id = data.get("id")

    updatable_fields = [
        "full_name",
        "mobile",
        "address_line_1",
        "address_line_2",
        "landmark",
        "city",
        "state",
        "country",
        "pincode",
        "address_type"
    ]

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT id
            FROM addresses
            WHERE id = %s
            AND user_id = %s
            AND is_deleted = FALSE
            """,
            [address_id, user_id]
        )

        if not cursor.fetchone():
            return {
                "message": "Address not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

    set_parts = []
    values = []

    for field in updatable_fields:
        if field in data:
            set_parts.append(f"{field} = %s")
            values.append(data[field])

    if "is_default" in data:

        if data["is_default"]:

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE addresses
                    SET is_default = FALSE
                    WHERE user_id = %s
                    AND is_deleted = FALSE
                    AND is_default = TRUE
                    AND id <> %s
                    """,
                    [user_id, address_id]
                )

            set_parts.append("is_default = %s")
            values.append(True)

        else:
            set_parts.append("is_default = %s")
            values.append(False)

    if not set_parts:
        return {
            "message": "No fields to update.",
            "data": {}
        }, status.HTTP_400_BAD_REQUEST

    set_parts.append("updated_by = %s")
    values.append(user_id)

    set_parts.append("updated_at = NOW()")

    values.append(address_id)
    values.append(user_id)

    sql = f"""
        UPDATE addresses
        SET {', '.join(set_parts)}
        WHERE id = %s
        AND user_id = %s
        AND is_deleted = FALSE
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, values)
        connection.commit()

    address_data, _ = get_addresses(
        user_id=user_id,
        address_id=address_id
    )

    return {
        "message": "Address updated successfully.",
        "data": address_data.get("data")
    }, status.HTTP_200_OK



def delete_address(address_id, user_id):

    if not address_id:
        return {
            "message": "id is required.",
            "data": {}
        }, status.HTTP_400_BAD_REQUEST

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT is_default
            FROM addresses
            WHERE id = %s
            AND user_id = %s
            AND is_deleted = FALSE
            """,
            [address_id, user_id]
        )

        row = cursor.fetchone()

        if not row:
            return {
                "message": "Address not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        was_default = row[0]

        cursor.execute(
            """
            UPDATE addresses
            SET
                is_deleted = TRUE,
                is_default = FALSE,
                updated_by = %s,
                updated_at = NOW()
            WHERE id = %s
            AND user_id = %s
            """,
            [user_id, address_id, user_id]
        )

        if was_default:

            cursor.execute(
                """
                UPDATE addresses
                SET is_default = TRUE
                WHERE id = (
                    SELECT id
                    FROM addresses
                    WHERE user_id = %s
                    AND is_deleted = FALSE
                    ORDER BY created_at DESC
                    LIMIT 1
                )
                """,
                [user_id]
            )

        connection.commit()

    return {
        "message": "Address deleted successfully.",
        "data": {}
    }, status.HTTP_200_OK



def create_notify_me_request(validated_data, user_id=None):

    variant_size_id = validated_data["variant_size_id"]
    email = validated_data["email"].strip().lower()

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                pvs.stock_quantity,
                pvs.size,
                v.color,
                p.name
            FROM product_variant_sizes pvs
            INNER JOIN product_variants v ON v.id = pvs.variant_id
            INNER JOIN products p ON p.id = v.product_id
            WHERE pvs.id = %s
            AND pvs.is_deleted = FALSE
            """,
            [variant_size_id]
        )

        row = cursor.fetchone()

        if not row:
            return {
                "message": "Product size not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        stock_quantity, size, color, product_name = row

        if stock_quantity and stock_quantity > 0:
            return {
                "message": "This size is already in stock.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        cursor.execute(
            """
            SELECT id
            FROM notify_me_requests
            WHERE variant_size_id = %s
            AND LOWER(email) = %s
            AND is_notified = FALSE
            AND is_deleted = FALSE
            """,
            [variant_size_id, email]
        )

        existing = cursor.fetchone()

        if existing:
            return {
                "message": "You will be notified by email when this size is back in stock.",
                "data": {"id": existing[0]}
            }, status.HTTP_200_OK

        cursor.execute(
            """
            INSERT INTO notify_me_requests
            (
                variant_size_id,
                email,
                user_id,
                created_at,
                updated_at
            )
            VALUES
            (
                %s,
                %s,
                %s,
                NOW(),
                NOW()
            )
            RETURNING id
            """,
            [variant_size_id, email, user_id]
        )

        notify_me_id = cursor.fetchone()[0]

        connection.commit()

    return {
        "message": "You will be notified by email when this size is back in stock.",
        "data": {
            "id": notify_me_id,
            "product_name": product_name,
            "color": color,
            "size": size
        }
    }, status.HTTP_201_CREATED



def get_notify_me_requests(variant_size_id=None, page=1, page_size=10):

    page = max(int(page), 1)
    page_size = max(int(page_size), 1)

    where_conditions = [
        "n.is_deleted = FALSE",
        "n.is_notified = FALSE"
    ]

    params = []

    if variant_size_id:
        where_conditions.append("n.variant_size_id = %s")
        params.append(variant_size_id)

    where_clause = " AND ".join(where_conditions)

    sql = f"""
        SELECT
            n.id,
            n.variant_size_id,
            n.email,
            n.user_id,
            n.created_at,
            pvs.size,
            pvs.stock_quantity,
            v.color,
            p.id AS product_id,
            p.name AS product_name
        FROM notify_me_requests n
        INNER JOIN product_variant_sizes pvs ON pvs.id = n.variant_size_id
        INNER JOIN product_variants v ON v.id = pvs.variant_id
        INNER JOIN products p ON p.id = v.product_id
        WHERE {where_clause}
        ORDER BY n.created_at DESC
    """

    with connection.cursor() as cursor:

        cursor.execute(sql, params)

        rows = cursor.fetchall()

        if not rows:
            return {
                "message": "Data not found.",
                "data": []
            }, status.HTTP_200_OK

        columns = [col[0] for col in cursor.description]

        result = db_query_result_to_json(rows, columns)

        paginated_list, pagination = paginate_queryset(
            result,
            page,
            page_size
        )

    return {
        "message": "Data fetched successfully.",
        "data": paginated_list,
        "pagination": pagination
    }, status.HTTP_200_OK



def delete_notify_me_request(notify_me_id, email):

    if not notify_me_id or not email:
        return {
            "message": "id and email are required.",
            "data": {}
        }, status.HTTP_400_BAD_REQUEST

    with connection.cursor() as cursor:

        cursor.execute(
            """
            UPDATE notify_me_requests
            SET
                is_deleted = TRUE,
                is_active = FALSE,
                updated_at = NOW()
            WHERE id = %s
            AND LOWER(email) = LOWER(%s)
            AND is_deleted = FALSE
            RETURNING id
            """,
            [notify_me_id, email.strip()]
        )

        if not cursor.fetchone():
            return {
                "message": "Notify me request not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        connection.commit()

    return {
        "message": "Notify me request cancelled successfully.",
        "data": {}
    }, status.HTTP_200_OK



def notify_users_for_restock(variant_size_id):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                n.id,
                n.email,
                pvs.size,
                v.color,
                p.name
            FROM notify_me_requests n
            INNER JOIN product_variant_sizes pvs ON pvs.id = n.variant_size_id
            INNER JOIN product_variants v ON v.id = pvs.variant_id
            INNER JOIN products p ON p.id = v.product_id
            WHERE n.variant_size_id = %s
            AND n.is_notified = FALSE
            AND n.is_deleted = FALSE
            """,
            [variant_size_id]
        )

        pending_requests = cursor.fetchall()

        if not pending_requests:
            return

        notified_ids = []

        for notify_me_id, email, size, color, product_name in pending_requests:

            send_restock_notification_email(
                email=email,
                product_name=product_name,
                color=color,
                size=size
            )

            notified_ids.append(notify_me_id)

        cursor.execute(
            """
            UPDATE notify_me_requests
            SET
                is_notified = TRUE,
                is_active = FALSE,
                notified_at = NOW(),
                updated_at = NOW()
            WHERE id = ANY(%s)
            """,
            [notified_ids]
        )

        connection.commit()
