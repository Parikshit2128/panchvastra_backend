from datetime import date, datetime, timedelta, timezone
import decimal
import html
import math
import random
import traceback
import uuid
import boto3
from botocore.config import Config as BotoConfig
import jwt
import os
import requests
from panchvastra.settings import BREVO_API_KEY, RUSTFS_ACCESS_KEY, RUSTFS_BUCKET_NAME, RUSTFS_ENDPOINT_URL, RUSTFS_PUBLIC_URL_BASE, RUSTFS_SECRET_KEY, SECRET_KEY
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, DataError, IntegrityError
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError, APIException
from django.http import Http404

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from panchvastra.settings import EMAIL_HOST, EMAIL_HOST_PASSWORD, EMAIL_HOST_USER, EMAIL_PORT
from django.http import JsonResponse




def db_query_result_to_json(query_result, column_names):
    def convert_value(val):
        try:
            if isinstance(val, decimal.Decimal):
                return float(val)
            elif isinstance(val, uuid.UUID):
                return str(val)
            elif isinstance(val, (datetime, date)):
                return val.isoformat()
            elif isinstance(val, dict):
                return val
            elif isinstance(val, list):
                return [convert_value(v) for v in val]
            else:
                return val
        except Exception as e:
            print(f"Failed to convert value: {val}, error: {e}")
            return str(val)

    if not query_result:
        return []

    if isinstance(query_result, tuple):
        return {column_names[i]: convert_value(query_result[i]) for i in range(len(column_names))}

    return [
        {column_names[i]: convert_value(row[i]) for i in range(len(column_names))}
        for row in query_result
    ]




MAX_PAGE_SIZE = 100


def clamp_page_size(page_size, default=10, maximum=MAX_PAGE_SIZE):
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        return default

    return max(1, min(page_size, maximum))


def clamp_page(page, default=1):
    try:
        page = int(page)
    except (TypeError, ValueError):
        return default

    return max(1, page)


def resolve_pagination(page, page_size, total_records):
    """Computes the (page, page_size, offset, pagination_dict) for a SQL
    LIMIT/OFFSET query against a table already known to hold `total_records`
    matching rows — the caller runs its own COUNT(*) first, so this never
    has to materialize the underlying rows just to paginate them.

    Mirrors Django's Paginator edge-case handling so this is a drop-in
    replacement for the old fetch-everything-then-paginate-in-Python
    approach: a non-integer page defaults to page 1, and a page number
    outside [1, total_pages] clamps to the last page.
    """
    page_size = clamp_page_size(page_size)
    total_pages = max(1, math.ceil(total_records / page_size))

    try:
        page = int(page)
        if page < 1 or page > total_pages:
            page = total_pages
    except (TypeError, ValueError):
        page = 1

    offset = (page - 1) * page_size

    pagination = {
        "current_page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_records": total_records,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }

    return page, page_size, offset, pagination


def generic_response_handler(business_func):

    def wrapper(request, *args, **kwargs):
        try:
            result = business_func(request, *args, **kwargs)

            if isinstance(result, Response):
                return result

            response_data, http_status = result

            if not isinstance(response_data, dict):
                response_data = {
                    "data": response_data
                }

            return Response({
                "success": 200 <= http_status < 300,
                **response_data  
            }, status=http_status)

        except ValidationError as e:
            return Response({
                "success": False,
                "message": e.detail,
                "data": {}
            }, status=status.HTTP_400_BAD_REQUEST)

        except Http404:
            return Response({
                "success": False,
                "message": "Resource not found",
                "data": {}
            }, status=status.HTTP_404_NOT_FOUND)

        except APIException as e:
            return Response({
                "success": False,
                "message": e.detail,
                "data": {}
            }, status=e.status_code)

        except DataError:
            # Typically a malformed id/number in a query param or body field
            # that failed a Postgres-side type cast (e.g. "id=abc").
            traceback.print_exc()
            connection.rollback()
            return Response({
                "success": False,
                "message": "Invalid request parameters.",
                "data": {}
            }, status=status.HTTP_400_BAD_REQUEST)

        except IntegrityError:
            # A uniqueness/FK constraint was violated, usually from a race
            # between two concurrent requests (e.g. duplicate coupon code).
            traceback.print_exc()
            connection.rollback()
            return Response({
                "success": False,
                "message": "This action conflicts with existing data. Please retry.",
                "data": {}
            }, status=status.HTTP_409_CONFLICT)

        except Exception:
            traceback.print_exc()
            return Response({
                "success": False,
                "message": "Internal Server Error",
                "data": {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return wrapper


def get_user_role_id():

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id
            FROM roles
            WHERE name = %s
              AND is_active = TRUE
              AND is_deleted = FALSE
            LIMIT 1
        """, ["User"])

        row = cursor.fetchone()

    return row[0] if row else None



def generate_otp_with_expiry():
    otp = f"{random.randint(100000, 999999)}"
    otp_expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    return otp, otp_expire


def _store_otp(cursor, user_id, otp, expires_at):
    cursor.execute("""
        INSERT INTO user_otps (user_id, otp, expires_at, created_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (user_id)
        DO UPDATE SET
            otp = EXCLUDED.otp,
            expires_at = EXCLUDED.expires_at,
            created_at = NOW()
    """, [user_id, otp, expires_at])



# def send_verification_otp(email, otp):
#     try:
#         url = "https://api.brevo.com/v3/smtp/email"

#         headers = {
#             "accept": "application/json",
#             "api-key": BREVO_API_KEY,
#             "content-type": "application/json"
#         }

#         payload = {
#             "sender": {
#                 "name": "Panchvastra",
#                 "email": "panchvastra9@gmail.com"
#             },
#             "to": [
#                 {
#                     "email": email
#                 }
#             ],
#             "subject": "Email Verification OTP",
#             "htmlContent": f"""
#                 <html>
#                     <body style="font-family: Arial, sans-serif;">
#                         <h2>Panchvastra</h2>
#                         <p>Your OTP for email verification is:</p>

#                         <div style="
#                             font-size:32px;
#                             font-weight:bold;
#                             letter-spacing:6px;
#                             color:#0d6efd;
#                             margin:20px 0;">
#                             {otp}
#                         </div>

#                         <p>This OTP is valid for <b>10 minutes</b>.</p>

#                         <hr>

#                         <small>
#                             If you didn't request this OTP, you can safely ignore this email.
#                         </small>
#                     </body>
#                 </html>
#             """
#         }

#         response = requests.post(
#             url,
#             headers=headers,
#             json=payload,
#             timeout=20
#         )

#         if response.status_code not in (200, 201):
#             raise Exception(
#                 f"Brevo API Error {response.status_code}: {response.text}"
#             )

#         print("OTP email sent successfully.")

#     except Exception:
#         traceback.print_exc()
#         raise


def send_verification_otp(email, otp):
    try:
        smtp_server = os.getenv("EMAIL_HOST")
        smtp_port = int(os.getenv("EMAIL_PORT"))
        smtp_email = os.getenv("EMAIL_HOST_USER")
        smtp_password = os.getenv("EMAIL_HOST_PASSWORD")

        message = MIMEMultipart("alternative")
        message["Subject"] = "Email Verification OTP"
        message["From"] = f"Panchvastra <{smtp_email}>"
        message["To"] = email

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Panchvastra</h2>

                <p>Your OTP for email verification is:</p>

                <div style="
                    font-size:32px;
                    font-weight:bold;
                    letter-spacing:6px;
                    color:#0d6efd;
                    margin:20px 0;">
                    {otp}
                </div>

                <p>This OTP is valid for <b>10 minutes</b>.</p>

                <hr>

                <small>
                    If you didn't request this OTP, you can safely ignore this email.
                </small>
            </body>
        </html>
        """

        message.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(
                smtp_email,
                email,
                message.as_string()
            )

        print("OTP email sent successfully.")

    except Exception:
        traceback.print_exc()
        raise


def send_restock_notification_email(email, product_name, color, size):
    try:
        smtp_server = os.getenv("EMAIL_HOST")
        smtp_port = int(os.getenv("EMAIL_PORT"))
        smtp_email = os.getenv("EMAIL_HOST_USER")
        smtp_password = os.getenv("EMAIL_HOST_PASSWORD")

        safe_product_name = html.escape(str(product_name))
        safe_color = html.escape(str(color))
        safe_size = html.escape(str(size))

        message = MIMEMultipart("alternative")
        message["Subject"] = f"{safe_product_name} is back in stock!"
        message["From"] = f"Panchvastra <{smtp_email}>"
        message["To"] = email

        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Panchvastra</h2>

                <p>Good news! The item you were waiting for is back in stock:</p>

                <div style="
                    font-size:18px;
                    font-weight:bold;
                    color:#0d6efd;
                    margin:20px 0;">
                    {safe_product_name} - {safe_color} - {safe_size}
                </div>

                <p>Hurry, grab it before it runs out again.</p>

                <hr>

                <small>
                    You are receiving this email because you asked to be notified
                    when this item was back in stock.
                </small>
            </body>
        </html>
        """

        message.attach(MIMEText(body, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(
                smtp_email,
                email,
                message.as_string()
            )

        print(f"Restock notification email sent to {email}.")
        return True

    except Exception:
        traceback.print_exc()
        return False


def decode_jwt_token(token):

    if not token:
        raise ValueError("Authorization token is missing.")

    token = token.strip()

    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        raise ValueError("Authorization token is empty.")

    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=["HS256"]
    )

_s3_client = None


def _get_s3_client():
    global _s3_client

    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=RUSTFS_ENDPOINT_URL,
            aws_access_key_id=RUSTFS_ACCESS_KEY,
            aws_secret_access_key=RUSTFS_SECRET_KEY,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"}
            ),
        )

    return _s3_client


def upload_image_to_storage(image, folder):

    object_key = f"{folder.strip('/')}/{uuid.uuid4()}_{image.name}"

    extra_args = {}
    if getattr(image, "content_type", None):
        extra_args["ContentType"] = image.content_type

    _get_s3_client().upload_fileobj(
        image,
        RUSTFS_BUCKET_NAME,
        object_key,
        ExtraArgs=extra_args
    )

    return {
        "url": f"{RUSTFS_PUBLIC_URL_BASE.rstrip('/')}/{object_key}",
        "file_id": object_key,
        "name": image.name
    }



def delete_image_from_storage(file_id):

    if not file_id:
        return

    _get_s3_client().delete_object(
        Bucket=RUSTFS_BUCKET_NAME,
        Key=file_id
    )


def validate_image_files(files):
    """Runs each uploaded file through the same ImageField validator
    CreateCategorySerializer/UpdateCategorySerializer already use for the
    category image, so a corrupt/non-image upload is rejected before it
    ever reaches storage.
    """
    image_field = serializers.ImageField()
    validated = []

    for file in files:
        try:
            validated.append(image_field.run_validation(file))
        except ValidationError as e:
            raise ValidationError({"images": e.detail})
        except DjangoValidationError as e:
            # ImageField.to_internal_value defers straight to Django's form
            # field and doesn't convert its ValidationError itself — DRF
            # normally does that conversion one level up, inside
            # Serializer.to_internal_value, which we bypass by validating
            # each file directly.
            raise ValidationError({"images": e.messages})

    return validated


# def replace_image(
#     old_file_id,
#     new_image,
#     folder
# ):

#     delete_image(old_file_id)

#     return upload_image(
#         new_image,
#         folder
#     )