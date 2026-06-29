from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from pv_app.api.serializer.sz_authentication import UserLoginSerializer, UserRegistrationSerializer, VerifyEmailSerializer


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



verify_email_swagger = extend_schema_view(
    
    post=extend_schema(
        tags=["Authentication"],
        description="Verify user email.",
        request=VerifyEmailSerializer,
    )
)