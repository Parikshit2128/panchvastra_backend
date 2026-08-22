from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from pv_app.api.serializer.sz_authentication import AdminLoginSerializer, UpdateUserProfileSerializer, UserLoginSerializer, UserRegistrationSerializer, VerifyEmailSerializer


register_user_swagger = extend_schema_view(
    
    post=extend_schema(
        tags=["Authentication"],
        description="Register a new user.",
        request=UserRegistrationSerializer,
    )
)


login_user_swagger = extend_schema_view(
    
    post=extend_schema(
        tags=["Authentication"],
        description="Login an existing user.",
        request=UserLoginSerializer,
    )
)


login_admin_swagger = extend_schema_view(
    
    post=extend_schema(
        tags=["Admin"],
        description="Login an existing admin.",
        request=AdminLoginSerializer,
    )
)



verify_email_swagger = extend_schema_view(

    post=extend_schema(
        tags=["Authentication"],
        description="Verify user email.",
        request=VerifyEmailSerializer,
    )
)


user_profile_swagger = extend_schema_view(

    get=extend_schema(
        tags=["Profile"],
        summary="Get profile",
        description="Fetch the authenticated user's profile details.",
    ),

    put=extend_schema(
        tags=["Profile"],
        summary="Update profile",
        description="Update the authenticated user's profile details.",
        request=UpdateUserProfileSerializer,
    ),
)