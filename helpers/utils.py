from datetime import date, datetime
import decimal
import uuid
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, APIException
from django.http import Http404



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
            return Response({
                "success": False,
                "message": "Internal Server Error",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return wrapper
