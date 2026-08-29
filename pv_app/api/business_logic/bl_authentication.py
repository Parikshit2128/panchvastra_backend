from django.db import connection
from datetime import datetime, timedelta
from helpers.utils import _store_otp, generate_otp_with_expiry, send_verification_otp, upload_image_to_imagekit
import jwt
from datetime import datetime, timedelta, timezone

from panchvastra.settings import SECRET_KEY
from django.contrib.auth.hashers import check_password


USER_PROFILE_COLUMNS = [
    "id",
    "role_id",
    "first_name",
    "last_name",
    "email",
    "mobile",
    "profile_image",
    "date_of_birth",
    "gender",
    "email_verified",
    "is_active",
    "total_orders",
    "total_spent",
    "last_order_at",
    "created_at"
]


def _serialize_user_profile(row):
    (
        id,
        role_id,
        first_name,
        last_name,
        email,
        mobile,
        profile_image,
        date_of_birth,
        gender,
        email_verified,
        is_active,
        total_orders,
        total_spent,
        last_order_at,
        created_at
    ) = row

    return {
        "id": id,
        "role_id": role_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "mobile": mobile,
        "profile_image": profile_image,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "email_verified": email_verified,
        "is_active": is_active,
        "total_orders": total_orders or 0,
        "total_spent": float(total_spent) if total_spent is not None else 0.0,
        "last_order_at": last_order_at,
        "created_at": created_at
    }


def register_user_logic(data):
    email = data["email"].lower().strip()
    first_name = data["first_name"]
    last_name = data.get("last_name")
    mobile = data.get("mobile")
    role_id = data.get("role_id", 2)

    otp, otp_expiry = generate_otp_with_expiry()

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, email_verified FROM users WHERE email=%s AND is_deleted=FALSE",
            [email]
        )
        user = cursor.fetchone()

        if user:
            user_id, email_verified = user

            if email_verified:
                return {"message": "User already registered. Please login."}, 400

            cursor.execute("""
                UPDATE users SET updated_at=NOW()
                WHERE id=%s
            """, [user_id])

            _store_otp(cursor, user_id, otp, otp_expiry)

            connection.commit()
            send_verification_otp(email, otp)

            return {"message": "OTP resent to email."}, 200

        cursor.execute("""
            INSERT INTO users (role_id, first_name, last_name, email, mobile, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, [role_id, first_name, last_name, email, mobile])

        user_id = cursor.fetchone()[0]

        _store_otp(cursor, user_id, otp, otp_expiry)

        connection.commit()
        send_verification_otp(email, otp)

        return {"message": "User registered. OTP sent to email."}, 201
    


def login_user_logic(data):
    email = data["email"].lower().strip()

    otp, otp_expiry = generate_otp_with_expiry()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, email_verified
            FROM users
            WHERE email=%s AND is_deleted=FALSE AND is_active=TRUE
        """, [email])

        row = cursor.fetchone()

        # Deliberately generic: don't reveal via status code or message
        # whether this email is registered/verified (account enumeration).
        generic_response = (
            {"message": "If this email is registered and verified, an OTP has been sent."},
            200
        )

        if not row:
            return generic_response

        user_id, email_verified = row

        if not email_verified:
            return generic_response

        _store_otp(cursor, user_id, otp, otp_expiry)

        connection.commit()
        send_verification_otp(email, otp)

        return generic_response
    


def verify_user_email_logic(data):
    email = data["email"].lower().strip()
    otp = data["otp"]

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                id,
                role_id,
                first_name,
                last_name,
                email,
                mobile,
                profile_image,
                date_of_birth,
                gender,
                email_verified,
                is_active,
                total_orders,
                total_spent,
                last_order_at,
                created_at
            FROM users
            WHERE email=%s
              AND is_deleted=FALSE
              AND is_active=TRUE
        """, [email])

        user = cursor.fetchone()

        if not user:
            return {"message": "User not found."}, 404

        (
            user_id,
            role_id,
            first_name,
            last_name,
            email,
            mobile,
            profile_image,
            date_of_birth,
            gender,
            email_verified,
            is_active,
            total_orders,
            total_spent,
            last_order_at,
            created_at
        ) = user

        cursor.execute("""
            SELECT otp, expires_at
            FROM user_otps
            WHERE user_id=%s
        """, [user_id])

        otp_row = cursor.fetchone()

        if not otp_row:
            return {"message": "OTP not found. Please request again."}, 400

        db_otp, expires_at = otp_row

        if datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
            return {"message": "OTP expired."}, 400

        if otp != db_otp:
            return {"message": "Invalid OTP."}, 400

        cursor.execute("""
            UPDATE users
            SET
                email_verified = TRUE,
                last_login_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, [user_id])

        cursor.execute("""
            DELETE FROM user_otps
            WHERE user_id = %s
        """, [user_id])
                
        connection.commit()

    payload = {
        "user_id": user_id,
        "user_role_id": role_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=15)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return {
        "message": "Email verified successfully.",
        "token": token,
        "user": {
            "id": user_id,
            "role_id": role_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile": mobile,
            "profile_image": profile_image,
            "date_of_birth": date_of_birth,
            "gender": gender,
            "email_verified": True,
            "is_active": is_active,
            "total_orders": total_orders or 0,
            "total_spent": float(total_spent) if total_spent is not None else 0.0,
            "last_order_at": last_order_at,
            "created_at": created_at
        }
    }, 200



def login_admin_logic(data):
    email = data["email"].lower().strip()
    password = data["password"]

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                id,
                role_id,
                first_name,
                last_name,
                email,
                mobile,
                password_hash,
                profile_image
            FROM users
            WHERE email=%s
              AND role_id = 1
              AND is_deleted=FALSE
              AND is_active=TRUE
        """, [email])

        user = cursor.fetchone()

        if not user:
            return {"message": "Invalid email or password."}, 401

        (
            user_id,
            role_id,
            first_name,
            last_name,
            email,
            mobile,
            password_hash,
            profile_image
        ) = user

        if not password_hash or not check_password(password, password_hash):
            return {"message": "Invalid email or password."}, 401

        cursor.execute("""
            UPDATE users
            SET last_login_at = NOW()
            WHERE id = %s
        """, [user_id])

        connection.commit()

    payload = {
        "user_id": user_id,
        "user_role_id": role_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=15)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return {
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": user_id,
            "role_id": role_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile": mobile,
            "profile_image": profile_image
        }
    }, 200



def get_user_profile_logic(user_id):

    columns_str = ", ".join(USER_PROFILE_COLUMNS)

    with connection.cursor() as cursor:

        cursor.execute(
            f"""
            SELECT {columns_str}
            FROM users
            WHERE id = %s
            AND is_deleted = FALSE
            """,
            [user_id]
        )

        row = cursor.fetchone()

    if not row:
        return {"message": "User not found."}, 404

    return {
        "message": "Profile fetched successfully.",
        "data": _serialize_user_profile(row)
    }, 200



def update_user_profile_logic(data, user_id):

    updatable_fields = [
        "first_name",
        "last_name",
        "mobile",
        "date_of_birth",
        "gender"
    ]

    image = data.get("profile_image")

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
            AND is_deleted = FALSE
            """,
            [user_id]
        )

        if not cursor.fetchone():
            return {"message": "User not found."}, 404

    set_parts = []
    values = []

    for field in updatable_fields:
        if field in data:
            set_parts.append(f"{field} = %s")
            values.append(data[field])

    if image:
        uploaded = upload_image_to_imagekit(
            image=image,
            folder="/profile_images"
        )

        set_parts.append("profile_image = %s")
        values.append(uploaded["url"])

    if not set_parts:
        return {"message": "No fields to update."}, 400

    set_parts.append("updated_at = NOW()")

    values.append(user_id)

    sql = f"""
        UPDATE users
        SET {', '.join(set_parts)}
        WHERE id = %s
        AND is_deleted = FALSE
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, values)
        connection.commit()

    profile_data, _ = get_user_profile_logic(user_id)

    return {
        "message": "Profile updated successfully.",
        "data": profile_data.get("data")
    }, 200