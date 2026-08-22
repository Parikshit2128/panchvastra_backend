from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from helpers.middleware import user_authentication_required
from helpers.utils import generic_response_handler
from pv_app.api.business_logic.bl_authentication import get_user_profile_logic, login_admin_logic, login_user_logic, register_user_logic, update_user_profile_logic, verify_user_email_logic
from pv_app.api.serializer.sz_authentication import AdminLoginSerializer, UpdateUserProfileSerializer, UserLoginSerializer, UserRegistrationSerializer, VerifyEmailSerializer

from pv_app.api.swagger.swag_authentication import register_user_swagger, login_user_swagger, verify_email_swagger, login_admin_swagger, user_profile_swagger


@register_user_swagger
@api_view(['POST'])
@generic_response_handler
def register_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return register_user_logic(serializer.validated_data)


@login_user_swagger
@api_view(['POST'])
@generic_response_handler
def login_user(request):
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return login_user_logic(serializer.validated_data)



@login_admin_swagger
@api_view(['POST'])
@generic_response_handler
def login_admin(request):
    serializer = AdminLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return login_admin_logic(serializer.validated_data)


@verify_email_swagger
@api_view(['POST'])
@generic_response_handler
def verify_email(request):
    serializer = VerifyEmailSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return verify_user_email_logic(serializer.validated_data)


@user_profile_swagger
@user_authentication_required()
@api_view(['GET', 'PUT'])
@parser_classes([MultiPartParser, FormParser])
@generic_response_handler
def user_profile(request):

    user_id = request.user_id

    if request.method == "GET":
        return get_user_profile_logic(user_id)

    serializer = UpdateUserProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return update_user_profile_logic(serializer.validated_data, user_id)

