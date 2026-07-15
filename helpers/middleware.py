from functools import wraps
from django.http import JsonResponse
from django.db import connection
import jwt
from rest_framework.response import Response
from rest_framework import status


from helpers.utils import decode_jwt_token

def user_authentication_required(role_required=None):
    """
    JWT Authentication decorator.

    Supports:
        @user_authentication_required()
        @user_authentication_required(role_required=2)
        @user_authentication_required(role_required=[1, 2])
        @user_authentication_required(role_required=(1, 2, 3))
    """

    def decorator(view_func):

        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):

            auth_header = request.headers.get("Authorization")

            if not auth_header:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Authorization token missing.",
                        "data": {}
                    },
                    status=401,
                )

            try:
                decoded_data = decode_jwt_token(auth_header)

                user_id = decoded_data.get("user_id")
                user_role_id = decoded_data.get("user_role_id")

                if user_id is None or user_role_id is None:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Invalid token payload.",
                            "data": {}
                        },
                        status=401,
                    )

                request.user_id = user_id
                request.role_id = user_role_id
                request.jwt_payload = decoded_data

            except ValueError as e:
                return JsonResponse(
                    {
                        "success": False,
                        "message": str(e),
                        "data": {}
                    },
                    status=401,
                )

            except jwt.ExpiredSignatureError:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Token has expired.",
                        "data": {}
                    },
                    status=401,
                )

            except jwt.InvalidTokenError as e:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Invalid authentication token.",
                        "error": str(e),
                        "data": {}
                    },
                    status=401,
                )

            if role_required is not None:

                if isinstance(role_required, int):
                    allowed_roles = {role_required}

                elif isinstance(role_required, (list, tuple, set)):
                    allowed_roles = set(role_required)

                else:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Invalid role configuration.",
                            "data": {}
                        },
                        status=500,
                    )

                if user_role_id not in allowed_roles:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "You are not authorized to access this resource.",
                            "data": {}
                        },
                        status=403,
                    )

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator