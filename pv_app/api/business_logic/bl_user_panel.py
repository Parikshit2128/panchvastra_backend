import json
import math

from django.db import connection
from rest_framework import status

from helpers.utils import db_query_result_to_json, paginate_queryset

def create_category(data, user_id):

    name = data.get("name")
    description = data.get("description")
    image_url = data.get("image_url")
    is_active = data.get("is_active", True)

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
            RETURNING id
            """,
            [
                name,
                description,
                image_url,
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

    updatable_fields = [
        "name",
        "description",
        "image_url",
        "is_active"
    ]

    set_parts = []
    values = []

    for field in updatable_fields:

        if field in data:

            if field == "name":

                with connection.cursor() as cursor:

                    cursor.execute(
                        """
                        SELECT 1
                        FROM categories
                        WHERE LOWER(name)=LOWER(%s)
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

    if not set_parts:
        return {
            "message": "No fields to update."
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

        if cursor.rowcount == 0:
            return {
                "message": "Category not found."
            }, status.HTTP_404_NOT_FOUND

        connection.commit()

    return {
        "message": "Category deleted successfully.",
        "data": {}
    }, status.HTTP_200_OK



def get_products(
    page=1,
    page_size=20,
    product_id=None,
    category_id=None,
    sub_category_id=None,
    size=None,
    min_price=None,
    max_price=None,
    search=None,
    sort_by="latest"
):

    page = max(int(page), 1)
    page_size = max(int(page_size), 1)

    where_conditions = [
        "p.is_deleted = FALSE",
        "p.is_active = TRUE"
    ]

    params = []

    if product_id:
        where_conditions.append("p.id = %s")
        params.append(product_id)

    if category_id:
        where_conditions.append("p.category_id = %s")
        params.append(category_id)

    if sub_category_id:
        where_conditions.append("p.sub_category_id = %s")
        params.append(sub_category_id)

    # For size stored as: S,M,L,XL
    if size:
        where_conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM unnest(
                    string_to_array(
                        REPLACE(p.size, ' ', ''),
                        ','
                    )
                ) sz
                WHERE LOWER(sz) = LOWER(%s)
            )
            """
        )
        params.append(size)

    if min_price:
        where_conditions.append(
            "p.selling_price >= %s"
        )
        params.append(min_price)

    if max_price:
        where_conditions.append(
            "p.selling_price <= %s"
        )
        params.append(max_price)

    if search:
        where_conditions.append(
            """
            (
                p.name ILIKE %s
                OR p.description ILIKE %s
                OR p.fabric ILIKE %s
                OR p.color ILIKE %s
            )
            """
        )

        search_term = f"%{search}%"

        params.extend([
            search_term,
            search_term,
            search_term,
            search_term
        ])

    where_clause = " AND ".join(where_conditions)

    sort_mapping = {
        "price_low_to_high": "p.selling_price ASC",
        "price_high_to_low": "p.selling_price DESC",
        "latest": "p.created_at DESC",
        "oldest": "p.created_at ASC"
    }

    order_by = sort_mapping.get(
        sort_by,
        "p.created_at DESC"
    )

    # ------------------------
    # Total Count
    # ------------------------

    count_sql = f"""
        SELECT COUNT(DISTINCT p.id)
        FROM products p
        WHERE {where_clause}
    """

    with connection.cursor() as cursor:

        cursor.execute(count_sql, params)

        total_records = cursor.fetchone()[0]

        if total_records == 0:
            return {
                "message": "Data not found.",
                "data": []
            }, status.HTTP_200_OK

    offset = (page - 1) * page_size

    # ------------------------
    # Main Query
    # ------------------------

    sql = f"""
        SELECT
            p.id,
            p.name,
            p.description,
            p.fabric,
            p.gsm,
            p.color,
            p.size,
            p.mrp,
            p.selling_price,
            p.cost_price,
            p.stock_quantity,
            p.is_featured,
            p.is_new_arrival,
            p.created_at,

            c.id AS category_id,
            c.name AS category_name,

            sc.id AS sub_category_id,
            sc.name AS sub_category_name,

            pt.id AS tag_id,
            pt.name AS tag_name,

            COALESCE(
                json_agg(
                    DISTINCT jsonb_build_object(
                        'id', pi.id,
                        'image_url', pi.image_url,
                        'display_order', pi.display_order
                    )
                    ORDER BY
                        jsonb_build_object(
                            'id', pi.id,
                            'image_url', pi.image_url,
                            'display_order', pi.display_order
                        )
                ) FILTER (
                    WHERE pi.id IS NOT NULL
                ),
                '[]'
            ) AS images

        FROM products p

        INNER JOIN categories c
            ON c.id = p.category_id
            AND c.is_deleted = FALSE

        INNER JOIN sub_categories sc
            ON sc.id = p.sub_category_id
            AND sc.is_deleted = FALSE

        INNER JOIN product_tags pt
            ON pt.id = p.tag_id
            AND pt.is_deleted = FALSE

        LEFT JOIN product_images pi
            ON pi.product_id = p.id
            AND pi.is_deleted = FALSE
            AND pi.is_active = TRUE

        WHERE {where_clause}

        GROUP BY
            p.id,
            c.id,
            sc.id,
            pt.id

        ORDER BY {order_by}

        LIMIT %s
        OFFSET %s
    """

    query_params = params + [
        page_size,
        offset
    ]

    with connection.cursor() as cursor:

        cursor.execute(sql, query_params)

        rows = cursor.fetchall()

        columns = [
            "id",
            "name",
            "description",
            "fabric",
            "gsm",
            "color",
            "size",
            "mrp",
            "selling_price",
            "cost_price",
            "stock_quantity",
            "is_featured",
            "is_new_arrival",
            "created_at",
            "category_id",
            "category_name",
            "sub_category_id",
            "sub_category_name",
            "tag_id",
            "tag_name",
            "images"
        ]

        result = []

        for row in rows:

            item = dict(zip(columns, row))

            item["discount_percentage"] = (
                round(
                    (
                        (
                            float(item["mrp"])
                            - float(item["selling_price"])
                        )
                        / float(item["mrp"])
                    ) * 100
                )
                if item["mrp"] and item["mrp"] > 0
                else 0
            )

            item["category"] = {
                "id": item.pop("category_id"),
                "name": item.pop("category_name")
            }

            item["sub_category"] = {
                "id": item.pop("sub_category_id"),
                "name": item.pop("sub_category_name")
            }

            item["tag"] = {
                "id": item.pop("tag_id"),
                "name": item.pop("tag_name")
            }

            if isinstance(item["images"], str):
                item["images"] = json.loads(
                    item["images"]
                )

            result.append(item)

    if product_id:

        return {
            "message": "Data fetched successfully.",
            "data": result[0] if result else {}
        }, status.HTTP_200_OK

    pagination = {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": math.ceil(
            total_records / page_size
        ),
        "has_next": (
            page * page_size
        ) < total_records,
        "has_previous": page > 1
    }

    return {
        "message": "Data fetched successfully.",
        "data": result,
        "pagination": pagination
    }, status.HTTP_200_OK