from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from pv_app.api.serializer.sz_authentication import AdminLoginSerializer, GoogleLoginSerializer, UpdateUserProfileSerializer, UserLoginSerializer, UserRegistrationSerializer, VerifyEmailSerializer


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


google_login_swagger = extend_schema_view(

    post=extend_schema(
        tags=["Authentication"],
        summary="Login / signup with Google",
        description=(
            "Exchanges a Google ID token for this API's own JWT. Send the "
            "`credential` string that Google Identity Services returns in "
            "the browser — no email or name, those are read from the "
            "token's verified claims.\n\n"
            "Returns the same {token, user} shape as verify_email, so the "
            "frontend can reuse its existing post-login handling. 200 means "
            "an existing account (an OTP account with the same email is "
            "linked to Google on the spot), 201 means a new account was "
            "created.\n\n"
            "Google supplies no phone number, so a freshly created user has "
            "mobile = null — collect it via PUT /user_profile/ before "
            "checkout.\n\n"
            "401 = token invalid or expired, 403 = unverified Google email "
            "or a deactivated/admin account, 409 = the email already "
            "belongs to a different Google account."
        ),
        request=GoogleLoginSerializer,
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