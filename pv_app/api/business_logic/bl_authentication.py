from django.db import connection
from datetime import datetime, timedelta
from helpers.utils import _store_otp, generate_otp_with_expiry, send_verification_otp
import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "your-secret"


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
            INSERT INTO users (role_id, first_name, last_name, email, mobile)
            VALUES (%s, %s, %s, %s, %s)
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

        if not row:
            return {"message": "User not found."}, 404

        user_id, email_verified = row

        if not email_verified:
            return {"message": "User not verified."}, 400

        _store_otp(cursor, user_id, otp, otp_expiry)

        connection.commit()
        # send_verification_otp(email, otp)

        return {"message": "OTP sent to email."}, 200
    


def verify_user_email_logic(data):
    email = data["email"].lower().strip()
    otp = data["otp"]

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT id, role_id, first_name, last_name, email
            FROM users
            WHERE email=%s AND is_deleted=FALSE AND is_active=TRUE
        """, [email])

        user = cursor.fetchone()

        if not user:
            return {"message": "User not found."}, 404

        user_id, role_id, first_name, last_name, email = user

        # get latest OTP
        cursor.execute("""
            SELECT otp, expires_at
            FROM user_otps
            WHERE user_id=%s
            ORDER BY created_at DESC
            LIMIT 1
        """, [user_id])

        otp_row = cursor.fetchone()

        if not otp_row:
            return {"message": "OTP not found. Please request again."}, 400

        db_otp, expires_at = otp_row

        # expiry check
        if datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
            return {"message": "OTP expired."}, 400

        if otp != db_otp:
            return {"message": "Invalid OTP."}, 400

        # verify user
        cursor.execute("""
            UPDATE users
            SET email_verified=TRUE,
                last_login_at=NOW()
            WHERE id=%s
        """, [user_id])

        connection.commit()

    # JWT
    payload = {
        "user_id": user_id,
        "role_id": role_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=15)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return {
        "message": "Email verified successfully.",
        "token": token
    }, 200