from functools import wraps
from django.http import JsonResponse
from django.db import connection
import jwt
from requests import Response
from rest_framework import status


from helpers.utils import decode_jwt_token

def user_authentication_required(role_required=None):
    """
    Decorator to check JWT and optionally validate user role by internal_id using raw SQL.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            token = request.headers.get('Authorization')
            if not token:
                return JsonResponse({'message': 'Authorization token missing!'}, status=401)

            try:
                decoded_data = decode_jwt_token(token)
                print("Decoded JWT data:", decoded_data)

                user_id = decoded_data.get('user_id')
                user_role_id = decoded_data.get('user_role_id')  

                request.user_id = user_id
                request.role_id = user_role_id

                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id
                        FROM public.roles
                        WHERE id = %s AND is_active = TRUE AND is_deleted = FALSE
                        """, [str(user_role_id)])
                    row = cursor.fetchone()
                    if not row:
                        return JsonResponse({'message': 'User role not found or inactive!'}, status=403)

                    request.role_id = row[0]

            except jwt.ExpiredSignatureError:
                return Response(
                    {"success": False, "message": "Token has expired!", "data": {}},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            except jwt.InvalidTokenError as e:
                return Response(
                    {"success": False, "message": "Token is invalid!", "error": str(e), "data": {}},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            except Exception as e:
                return Response(
                    {"success": False, "message": "Authentication failed", "error": str(e)},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if role_required and request.role_id != role_required:
                return Response(
                    {"success": False, "message": "Unauthorized access!", "data": {}},
                    status=status.HTTP_403_FORBIDDEN
                )   

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
