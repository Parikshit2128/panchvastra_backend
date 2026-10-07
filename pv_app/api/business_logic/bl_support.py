import math

from django.db import connection
from rest_framework import status

from helpers.utils import clamp_page, clamp_page_size
from pv_app.api.serializer.sz_support import (
    SUPPORT_CATEGORY_CHOICES,
    SUPPORT_CATEGORY_LABELS,
    SUPPORT_STATUS_CHOICES
)


SUPPORT_QUERY_COLUMNS = [
    "id",
    "user_id",
    "name",
    "email",
    "category",
    "message",
    "status",
    "created_at",
    "updated_at"
]


def _serialize_support_query(row):

    item = dict(zip(SUPPORT_QUERY_COLUMNS, row))

    item["category_label"] = SUPPORT_CATEGORY_LABELS.get(
        item["category"],
        item["category"]
    )

    return item


def create_support_query(data, user_id=None):
    """Store one Help Desk submission.

    user_id is None for an anonymous visitor. When the visitor happened to be
    logged in it links the query to their account, which is what lets an
    admin jump from a query to that customer's orders.
    """

    with connection.cursor() as cursor:

        cursor.execute(
            """
            INSERT INTO public.support_queries
            (
                user_id,
                name,
                email,
                category,
                message,
                status,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, 'OPEN', NOW(), NOW())
            RETURNING id
            """,
            [
                user_id,
                data["name"].strip(),
                data["email"].lower().strip(),
                data["category"],
                data["message"].strip()
            ]
        )

        query_id = cursor.fetchone()[0]

    # Only the id goes back: the form's job is done once it is stored, and a
    # public endpoint has no reason to echo the submission to whoever sent it.
    return {
        "message": "Thanks for reaching out. We'll get back to you soon.",
        "data": {"id": query_id}
    }, status.HTTP_201_CREATED


def get_support_queries(
    query_id=None,
    page=1,
    page_size=10,
    category=None,
    query_status=None,
    search=None
):
    columns_str = ", ".join(SUPPORT_QUERY_COLUMNS)

    if query_id:

        try:
            query_id = int(query_id)
        except (TypeError, ValueError):
            return {
                "message": "id must be an integer.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT {columns_str}
                FROM public.support_queries
                WHERE id = %s
                """,
                [query_id]
            )

            row = cursor.fetchone()

        if not row:
            return {
                "message": "Query not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        return {
            "message": "Data fetched successfully.",
            "data": _serialize_support_query(row)
        }, status.HTTP_200_OK

    if category and category not in SUPPORT_CATEGORY_LABELS:
        return {
            "message": "Invalid category.",
            "data": {
                "allowed": [value for value, _ in SUPPORT_CATEGORY_CHOICES]
            }
        }, status.HTTP_400_BAD_REQUEST

    if query_status and query_status not in SUPPORT_STATUS_CHOICES:
        return {
            "message": "Invalid status.",
            "data": {"allowed": SUPPORT_STATUS_CHOICES}
        }, status.HTTP_400_BAD_REQUEST

    page = clamp_page(page)
    page_size = clamp_page_size(page_size, default=10)
    offset = (page - 1) * page_size

    where_conditions = ["TRUE"]
    params = []

    if category:
        where_conditions.append("category = %s")
        params.append(category)

    if query_status:
        where_conditions.append("status = %s")
        params.append(query_status)

    if search:
        where_conditions.append("(name ILIKE %s OR email ILIKE %s)")
        params.extend([f"%{search}%"] * 2)

    where_clause = " AND ".join(where_conditions)

    with connection.cursor() as cursor:

        cursor.execute(
            f"SELECT COUNT(*) FROM public.support_queries WHERE {where_clause}",
            params
        )

        total_records = cursor.fetchone()[0]

        if total_records == 0:
            return {
                "message": "Data not found.",
                "data": [],
                "pagination": {}
            }, status.HTTP_200_OK

        # Open work first, then newest, so what still needs an answer is
        # what the admin sees at the top.
        cursor.execute(
            f"""
            SELECT {columns_str}
            FROM public.support_queries
            WHERE {where_clause}
            ORDER BY (status = 'RESOLVED') ASC, created_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset]
        )

        rows = cursor.fetchall()

    return {
        "message": "Data fetched successfully.",
        "data": [_serialize_support_query(row) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": math.ceil(total_records / page_size),
            "has_next": page * page_size < total_records,
            "has_previous": page > 1
        }
    }, status.HTTP_200_OK


def update_support_query_status(data):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            UPDATE public.support_queries
            SET
                status = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id
            """,
            [data["status"], data["id"]]
        )

        if not cursor.fetchone():
            return {
                "message": "Query not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

    return get_support_queries(query_id=data["id"])
