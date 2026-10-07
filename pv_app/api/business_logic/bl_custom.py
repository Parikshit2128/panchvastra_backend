import math
import uuid

from django.db import connection, transaction
from rest_framework import status

from helpers.utils import (
    clamp_page,
    clamp_page_size,
    delete_image_from_storage,
    upload_image_to_storage
)
from pv_app.api.business_logic.bl_user_panel import as_utc
from pv_app.api.serializer.sz_custom import CUSTOM_REQUEST_STATUSES


CUSTOM_REQUEST_STATUS_LABELS = {
    "NEW": "New",
    "IN_REVIEW": "In Review",
    "APPROVED": "Approved",
    "IN_PRODUCTION": "In Production",
    "SHIPPED": "Shipped",
    "DELIVERED": "Delivered",
    "CANCELLED": "Cancelled"
}

# option_type -> the key it is grouped under in the GET response.
OPTION_GROUP_KEYS = {
    "GARMENT": "garments",
    "COLOUR": "colours",
    "SIZE": "sizes",
    "PRINT_TYPE": "print_types"
}


def _full_name(first_name, last_name):
    return " ".join(part for part in [first_name, last_name] if part) or None


# --------------------------------------------------------------------------
# Options (garments, colours, sizes, print types)
# --------------------------------------------------------------------------

def get_custom_options(include_inactive=False):
    """Everything the "Build your piece" page needs, in one call.

    The customer view (include_inactive=False) hides switched-off options,
    hides a garment's switched-off colours, and drops any garment left with
    no colour at all, since it could never be ordered.
    """

    active_filter = "" if include_inactive else "AND is_active = TRUE"

    with connection.cursor() as cursor:

        cursor.execute(
            f"""
            SELECT id, option_type, name, description, hex_code,
                   image_url, display_order, is_active
            FROM public.custom_options
            WHERE is_deleted = FALSE
            {active_filter}
            ORDER BY display_order ASC NULLS LAST, id ASC
            """
        )

        option_rows = cursor.fetchall()

        colour_filter = "" if include_inactive else "AND c.is_active = TRUE"

        cursor.execute(
            f"""
            SELECT m.garment_id, m.colour_id
            FROM public.custom_garment_colours m
            JOIN public.custom_options c
                ON c.id = m.colour_id
                AND c.is_deleted = FALSE
                {colour_filter}
            ORDER BY c.display_order ASC NULLS LAST, c.id ASC
            """
        )

        garment_colours = {}

        for garment_id, colour_id in cursor.fetchall():
            garment_colours.setdefault(garment_id, []).append(colour_id)

    result = {key: [] for key in OPTION_GROUP_KEYS.values()}

    for row in option_rows:

        option_id, option_type, name, description, hex_code, image_url, display_order, is_active = row

        item = {
            "id": option_id,
            "name": name,
            "display_order": display_order
        }

        if option_type in ("GARMENT", "PRINT_TYPE"):
            item["description"] = description
            item["image_url"] = image_url

        if option_type == "COLOUR":
            item["hex_code"] = hex_code

        if option_type == "GARMENT":

            item["colour_ids"] = garment_colours.get(option_id, [])

            if not include_inactive and not item["colour_ids"]:
                continue

        if include_inactive:
            item["is_active"] = is_active

        result[OPTION_GROUP_KEYS[option_type]].append(item)

    return {
        "message": "Data fetched successfully.",
        "data": result
    }, status.HTTP_200_OK


def _check_colour_ids(cursor, colour_ids):
    """Returns the sorted unique ids if every one is an existing colour, else
    a 400 response tuple."""

    colour_ids = sorted(set(colour_ids))

    cursor.execute(
        """
        SELECT id
        FROM public.custom_options
        WHERE id = ANY(%s)
        AND option_type = 'COLOUR'
        AND is_deleted = FALSE
        """,
        [colour_ids]
    )

    found = {row[0] for row in cursor.fetchall()}
    missing = [colour_id for colour_id in colour_ids if colour_id not in found]

    if missing:
        return None, ({
            "message": "Some colour ids are not valid colours.",
            "data": {"invalid_colour_ids": missing}
        }, status.HTTP_400_BAD_REQUEST)

    return colour_ids, None


def _name_taken(cursor, option_type, name, exclude_id=None):

    cursor.execute(
        """
        SELECT 1
        FROM public.custom_options
        WHERE option_type = %s
        AND LOWER(name) = LOWER(%s)
        AND is_deleted = FALSE
        AND id <> %s
        """,
        [option_type, name, exclude_id or 0]
    )

    return cursor.fetchone() is not None


def _set_garment_colours(cursor, garment_id, colour_ids):
    """Replaces a garment's colour list with exactly colour_ids."""

    cursor.execute(
        "DELETE FROM public.custom_garment_colours WHERE garment_id = %s",
        [garment_id]
    )

    cursor.executemany(
        """
        INSERT INTO public.custom_garment_colours (garment_id, colour_id, created_at)
        VALUES (%s, %s, NOW())
        """,
        [(garment_id, colour_id) for colour_id in colour_ids]
    )


def create_custom_option(data, user_id):

    option_type = data["option_type"]
    name = data["name"].strip()
    image = data.get("image")

    # Only garments and print types show a picture on the page.
    if image and option_type not in ("GARMENT", "PRINT_TYPE"):
        return {
            "message": "Only a garment or a print type can have an image.",
            "data": {}
        }, status.HTTP_400_BAD_REQUEST

    with connection.cursor() as cursor:

        if _name_taken(cursor, option_type, name):
            return {
                "message": f"A {option_type.lower().replace('_', ' ')} named '{name}' already exists.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        colour_ids = None

        if option_type == "GARMENT":
            colour_ids, error = _check_colour_ids(cursor, data["colour_ids"])
            if error:
                return error

        display_order = data.get("display_order")

        # Omitted display_order means "put it last" within its own type.
        if display_order is None:
            cursor.execute(
                """
                SELECT COALESCE(MAX(display_order), 0)
                FROM public.custom_options
                WHERE option_type = %s
                AND is_deleted = FALSE
                """,
                [option_type]
            )
            display_order = cursor.fetchone()[0] + 1

    # Uploaded only after every check passes, so a rejected request never
    # leaves an orphan file in storage.
    uploaded = None

    if image:
        uploaded = upload_image_to_storage(image=image, folder="/custom-options")

    try:

        with transaction.atomic(), connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO public.custom_options
                (
                    option_type, name, description, hex_code,
                    image_url, image_file_id, display_order, is_active,
                    created_by, updated_by, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
                """,
                [
                    option_type,
                    name,
                    data.get("description"),
                    data.get("hex_code") if option_type == "COLOUR" else None,
                    uploaded["url"] if uploaded else None,
                    uploaded["file_id"] if uploaded else None,
                    display_order,
                    data.get("is_active", True),
                    user_id,
                    user_id
                ]
            )

            option_id = cursor.fetchone()[0]

            if colour_ids:
                _set_garment_colours(cursor, option_id, colour_ids)

    except Exception:
        if uploaded:
            delete_image_from_storage(uploaded["file_id"])
        raise

    return {
        "message": "Option created successfully.",
        "data": {"id": option_id}
    }, status.HTTP_201_CREATED


def update_custom_option(data, user_id):

    option_id = data["id"]
    image = data.get("image")

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT option_type, image_file_id
            FROM public.custom_options
            WHERE id = %s
            AND is_deleted = FALSE
            """,
            [option_id]
        )

        row = cursor.fetchone()

        if not row:
            return {
                "message": "Option not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        option_type, old_file_id = row

        if image and option_type not in ("GARMENT", "PRINT_TYPE"):
            return {
                "message": "Only a garment or a print type can have an image.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        if "hex_code" in data and option_type != "COLOUR":
            return {
                "message": "Only a colour has a hex code.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        if option_type == "COLOUR" and "hex_code" in data and not data["hex_code"]:
            return {
                "message": "A colour needs a hex code.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        if "colour_ids" in data and option_type != "GARMENT":
            return {
                "message": "Only a garment has colours.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        if "name" in data:
            data["name"] = data["name"].strip()
            if _name_taken(cursor, option_type, data["name"], exclude_id=option_id):
                return {
                    "message": f"A {option_type.lower().replace('_', ' ')} named '{data['name']}' already exists.",
                    "data": {}
                }, status.HTTP_400_BAD_REQUEST

        colour_ids = None

        if "colour_ids" in data:

            if not data["colour_ids"]:
                return {
                    "message": "A garment needs at least one colour.",
                    "data": {}
                }, status.HTTP_400_BAD_REQUEST

            colour_ids, error = _check_colour_ids(cursor, data["colour_ids"])
            if error:
                return error

    # Only the fields actually sent are written.
    set_parts = ["updated_by = %s", "updated_at = NOW()"]
    values = [user_id]

    for field in ("name", "description", "hex_code", "display_order"):
        if field in data:
            set_parts.append(f"{field} = %s")
            values.append(data[field])

    if data.get("is_active") is not None:
        set_parts.append("is_active = %s")
        values.append(data["is_active"])

    uploaded = None

    if image:
        uploaded = upload_image_to_storage(image=image, folder="/custom-options")
        set_parts.extend(["image_url = %s", "image_file_id = %s"])
        values.extend([uploaded["url"], uploaded["file_id"]])

    values.append(option_id)

    try:

        with transaction.atomic(), connection.cursor() as cursor:

            cursor.execute(
                f"""
                UPDATE public.custom_options
                SET {', '.join(set_parts)}
                WHERE id = %s
                AND is_deleted = FALSE
                """,
                values
            )

            if colour_ids is not None:
                _set_garment_colours(cursor, option_id, colour_ids)

    except Exception:
        if uploaded:
            delete_image_from_storage(uploaded["file_id"])
        raise

    # The old picture is removed only once the new one is safely recorded.
    # A failure here leaves an orphan file, never a broken image on the page.
    if uploaded and old_file_id:
        try:
            delete_image_from_storage(old_file_id)
        except Exception as e:
            print(f"[update_custom_option] could not delete old image {old_file_id}: {e}", flush=True)

    return {
        "message": "Option updated successfully.",
        "data": {"id": option_id}
    }, status.HTTP_200_OK


def delete_custom_option(option_id, user_id):
    """Soft delete. Past requests keep the option's name, because they store
    their own copy of what the customer picked."""

    try:
        option_id = int(option_id)
    except (TypeError, ValueError):
        return {
            "message": "id must be an integer.",
            "data": {}
        }, status.HTTP_400_BAD_REQUEST

    with connection.cursor() as cursor:

        cursor.execute(
            """
            UPDATE public.custom_options
            SET
                is_deleted = TRUE,
                is_active = FALSE,
                updated_by = %s,
                updated_at = NOW()
            WHERE id = %s
            AND is_deleted = FALSE
            RETURNING id
            """,
            [user_id, option_id]
        )

        if not cursor.fetchone():
            return {
                "message": "Option not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

    return {
        "message": "Option deleted successfully.",
        "data": {}
    }, status.HTTP_200_OK


# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------

def create_custom_request(data, user_id):

    picked = {
        "GARMENT": data["garment_id"],
        "COLOUR": data["colour_id"],
        "SIZE": data["size_id"],
        "PRINT_TYPE": data["print_type_id"]
    }

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT id, option_type, name
            FROM public.custom_options
            WHERE id = ANY(%s)
            AND is_deleted = FALSE
            AND is_active = TRUE
            """,
            [list(picked.values())]
        )

        found = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

        names = {}

        for option_type, option_id in picked.items():

            # The id must exist AND be of the right kind: a colour id sent as
            # garment_id is as wrong as a missing one.
            if option_id not in found or found[option_id][0] != option_type:
                field = f"{option_type.lower()}_id"
                return {
                    "message": "This option is no longer available. Please refresh and choose again.",
                    "data": {"field": field}
                }, status.HTTP_400_BAD_REQUEST

            names[option_type] = found[option_id][1]

        cursor.execute(
            """
            SELECT 1
            FROM public.custom_garment_colours
            WHERE garment_id = %s
            AND colour_id = %s
            """,
            [data["garment_id"], data["colour_id"]]
        )

        if not cursor.fetchone():
            return {
                "message": f"{names['GARMENT']} is not available in {names['COLOUR']}.",
                "data": {"field": "colour_id"}
            }, status.HTTP_400_BAD_REQUEST

    design_file = data.get("design_file")
    uploaded = None

    if design_file:
        uploaded = upload_image_to_storage(image=design_file, folder="/custom-designs")

    request_number = f"CST-{uuid.uuid4().hex[:8].upper()}"

    try:

        with transaction.atomic(), connection.cursor() as cursor:

            # The option names are copied onto the request on purpose: an
            # admin can later rename or delete an option, and the request
            # must still say exactly what the customer chose.
            cursor.execute(
                """
                INSERT INTO public.custom_requests
                (
                    request_number, user_id,
                    garment_id, colour_id, size_id, print_type_id,
                    garment_name, colour_name, size_name, print_type_name,
                    design_file_url, design_file_id, design_file_name,
                    design_description,
                    full_name, phone_country_code, phone_number,
                    status, created_at, updated_at
                )
                VALUES
                (
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s,
                    %s, %s, %s,
                    'NEW', NOW(), NOW()
                )
                RETURNING id
                """,
                [
                    request_number, user_id,
                    data["garment_id"], data["colour_id"], data["size_id"], data["print_type_id"],
                    names["GARMENT"], names["COLOUR"], names["SIZE"], names["PRINT_TYPE"],
                    uploaded["url"] if uploaded else None,
                    uploaded["file_id"] if uploaded else None,
                    design_file.name if design_file else None,
                    data.get("design_description"),
                    data["full_name"].strip(),
                    data["phone_country_code"],
                    data["phone_number"]
                ]
            )

            request_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO public.custom_request_history
                    (request_id, status, created_by, created_at)
                VALUES (%s, 'NEW', %s, NOW())
                """,
                [request_id, user_id]
            )

    except Exception:
        if uploaded:
            delete_image_from_storage(uploaded["file_id"])
        raise

    return get_custom_requests(
        user_id=user_id,
        request_id=request_id,
        success_message="Your request has been received. We'll contact you on WhatsApp.",
        success_status=status.HTTP_201_CREATED
    )


CUSTOM_REQUEST_COLUMNS = [
    "id", "request_number", "user_id",
    "garment_id", "colour_id", "size_id", "print_type_id",
    "garment_name", "colour_name", "size_name", "print_type_name",
    "design_file_url", "design_file_name", "design_description",
    "full_name", "phone_country_code", "phone_number",
    "status", "created_at", "updated_at"
]


def _serialize_request(row, is_admin):

    item = dict(zip(CUSTOM_REQUEST_COLUMNS + ["customer_email"], row))

    item["status_label"] = CUSTOM_REQUEST_STATUS_LABELS.get(item["status"], item["status"])
    item["created_at"] = as_utc(item["created_at"])
    item["updated_at"] = as_utc(item["updated_at"])

    if not is_admin:
        item.pop("customer_email", None)

    return item


def get_custom_requests(
    user_id=None,
    request_id=None,
    page=1,
    page_size=10,
    request_status=None,
    search=None,
    success_message="Data fetched successfully.",
    success_status=status.HTTP_200_OK
):
    """user_id scopes to one customer; None (admin) sees every request."""

    is_admin = user_id is None
    select_cols = ", ".join(f"r.{col}" for col in CUSTOM_REQUEST_COLUMNS)

    base_sql = f"""
        SELECT {select_cols}, u.email AS customer_email
        FROM public.custom_requests r
        LEFT JOIN public.users u ON u.id = r.user_id
    """

    where_conditions = ["r.is_deleted = FALSE"]
    params = []

    if user_id is not None:
        where_conditions.append("r.user_id = %s")
        params.append(user_id)

    if request_id is not None:

        try:
            request_id = int(request_id)
        except (TypeError, ValueError):
            return {
                "message": "id must be an integer.",
                "data": {}
            }, status.HTTP_400_BAD_REQUEST

        where_conditions.append("r.id = %s")
        params.append(request_id)

        with connection.cursor() as cursor:

            cursor.execute(
                f"{base_sql} WHERE {' AND '.join(where_conditions)}",
                params
            )

            row = cursor.fetchone()

            if not row:
                return {
                    "message": "Request not found.",
                    "data": {}
                }, status.HTTP_404_NOT_FOUND

            item = _serialize_request(row, is_admin)

            cursor.execute(
                """
                SELECT h.id, h.status, h.note, h.created_at, u.first_name, u.last_name
                FROM public.custom_request_history h
                LEFT JOIN public.users u ON u.id = h.created_by
                WHERE h.request_id = %s
                ORDER BY h.created_at DESC, h.id DESC
                """,
                [request_id]
            )

            history = []

            for history_id, history_status, note, created_at, first_name, last_name in cursor.fetchall():

                entry = {
                    "id": history_id,
                    "status": history_status,
                    "label": CUSTOM_REQUEST_STATUS_LABELS.get(history_status, history_status),
                    "created_at": as_utc(created_at)
                }

                # Admin notes are working notes for the team, not messages to
                # the customer, so the customer sees status changes only.
                if is_admin:
                    entry["note"] = note
                    entry["created_by"] = _full_name(first_name, last_name)
                elif not history_status:
                    # A note-only row (status NULL): internal, skip it.
                    continue

                history.append(entry)

            item["history"] = history

        return {
            "message": success_message,
            "data": item
        }, success_status

    if request_status:

        if request_status not in CUSTOM_REQUEST_STATUSES:
            return {
                "message": "Invalid status.",
                "data": {"allowed": CUSTOM_REQUEST_STATUSES}
            }, status.HTTP_400_BAD_REQUEST

        where_conditions.append("r.status = %s")
        params.append(request_status)

    # Search is offered to admins only; a customer has few enough requests
    # to scroll.
    if search and is_admin:
        where_conditions.append(
            "(r.request_number ILIKE %s OR r.full_name ILIKE %s OR r.phone_number ILIKE %s)"
        )
        params.extend([f"%{search}%"] * 3)

    where_clause = " AND ".join(where_conditions)

    page = clamp_page(page)
    page_size = clamp_page_size(page_size, default=10)
    offset = (page - 1) * page_size

    with connection.cursor() as cursor:

        cursor.execute(
            f"SELECT COUNT(*) FROM public.custom_requests r WHERE {where_clause}",
            params
        )

        total_records = cursor.fetchone()[0]

        if total_records == 0:
            return {
                "message": "Data not found.",
                "data": [],
                "pagination": {}
            }, status.HTTP_200_OK

        cursor.execute(
            f"""
            {base_sql}
            WHERE {where_clause}
            ORDER BY r.created_at DESC, r.id DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset]
        )

        rows = cursor.fetchall()

    return {
        "message": "Data fetched successfully.",
        "data": [_serialize_request(row, is_admin) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": math.ceil(total_records / page_size),
            "has_next": page * page_size < total_records,
            "has_previous": page > 1
        }
    }, status.HTTP_200_OK


@transaction.atomic
def update_custom_request(data, user_id):
    """Admin changes the status and/or adds a note. Every call that changes
    the status or carries a note leaves one history row."""

    request_id = data["id"]
    new_status = data.get("status")
    note = data.get("note")

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT status
            FROM public.custom_requests
            WHERE id = %s
            AND is_deleted = FALSE
            FOR UPDATE
            """,
            [request_id]
        )

        row = cursor.fetchone()

        if not row:
            return {
                "message": "Request not found.",
                "data": {}
            }, status.HTTP_404_NOT_FOUND

        current_status = row[0]
        status_changed = new_status is not None and new_status != current_status

        if status_changed:
            cursor.execute(
                """
                UPDATE public.custom_requests
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                """,
                [new_status, request_id]
            )

        if status_changed or note:

            # A note-only entry is stored with a NULL status, so the
            # customer's view (which shows status changes only) can skip it.
            cursor.execute(
                """
                INSERT INTO public.custom_request_history
                    (request_id, status, note, created_by, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                [request_id, new_status if status_changed else None, note, user_id]
            )

    return get_custom_requests(
        user_id=None,
        request_id=request_id,
        success_message="Request updated successfully."
    )
