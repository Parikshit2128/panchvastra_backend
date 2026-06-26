from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema_view,
    extend_schema,
)

from .serializers import CheckoutOrderSerializer


checkout_payment_schema = extend_schema_view(
    post=extend_schema(
        tags=["Payments"],
        summary="Create Razorpay Order",
        description="Creates a Razorpay order for one-time payment.",
        request=CheckoutOrderSerializer,
    ),
)