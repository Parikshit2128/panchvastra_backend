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


cod_order_schema = extend_schema_view(
    post=extend_schema(
        tags=["Payments"],
        summary="Place Cash on Delivery order",
        description=(
            "Places the order immediately for cash-on-delivery — no payment gateway "
            "involved. Stock is decremented and the cart is cleared as part of the "
            "same request, since there is no later webhook to reconcile them."
        ),
        request=CheckoutOrderSerializer,
    ),
)