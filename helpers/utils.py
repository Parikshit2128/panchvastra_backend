from datetime import date, datetime, timedelta, timezone
import decimal
import random
import traceback
import traceback
import uuid
import requests
from panchvastra.settings import BREVO_API_KEY
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import connection
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, APIException
from django.http import Http404

import smtplib
from email.mime.text import MIMEText

from panchvastra.settings import EMAIL_HOST, EMAIL_HOST_PASSWORD, EMAIL_HOST_USER, EMAIL_PORT



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




def paginate_queryset(qs, page, page_size):
    paginator = Paginator(qs, page_size)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page = 1
        page_obj = paginator.page(page)
    except EmptyPage:
        page = paginator.num_pages
        page_obj = paginator.page(page)

    pagination = {
        "current_page": page,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }

    return page_obj.object_list, pagination


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

        except Exception as e:
            traceback.print_exc()
            return Response({
                "success": False,
                "message": "Internal Server Error",
                "error": str(e)
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
        INSERT INTO user_otps (user_id, otp, expires_at)
        VALUES (%s, %s, %s)
    """, [user_id, otp, expires_at])



def send_verification_otp(email, otp):
    try:
        url = "https://api.brevo.com/v3/smtp/email"

        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        payload = {
            "sender": {
                "name": "Panchvastra",
                "email": "panchvastra9@gmail.com"
            },
            "to": [
                {
                    "email": email
                }
            ],
            "subject": "Email Verification OTP",
            "htmlContent": f"""
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
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=20
        )

        if response.status_code not in (200, 201):
            raise Exception(
                f"Brevo API Error {response.status_code}: {response.text}"
            )

        print("OTP email sent successfully.")

    except Exception:
        traceback.print_exc()
        raise