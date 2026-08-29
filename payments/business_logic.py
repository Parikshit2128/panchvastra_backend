import uuid
from django.db import connection, transaction
from django.conf import settings
from rest_framework.response import Response

from .services.razorpay_client import client
import json
import hmac
import hashlib


def _validate_coupon(cursor, coupon_code, user_id, subtotal):
    """Returns {"coupon_id": ..., "discount_amount": ...} or {"error": "..."}."""

    cursor.execute("""
        SELECT
            id, discount_type, discount_value, maximum_discount_amount,
            minimum_order_amount, max_usage, used_count, max_usage_per_user,
            is_first_order_only
        FROM public.coupons
        WHERE UPPER(code) = UPPER(%s)
        AND is_active = TRUE
        AND is_deleted = FALSE
        AND start_date <= CURRENT_DATE
        AND end_date >= CURRENT_DATE
    """, [coupon_code])

    row = cursor.fetchone()

    if not row:
        return {"error": "Invalid or expired coupon code."}

    (
        coupon_id,
        discount_type,
        discount_value,
        maximum_discount_amount,
        minimum_order_amount,
        max_usage,
        used_count,
        max_usage_per_user,
        is_first_order_only
    ) = row

    if minimum_order_amount and subtotal < float(minimum_order_amount):
        return {"error": f"Minimum order amount for this coupon is {minimum_order_amount}."}

    if max_usage is not None and used_count >= max_usage:
        return {"error": "This coupon has reached its usage limit."}

    if max_usage_per_user is not None:

        cursor.execute("""
            SELECT COUNT(*)
            FROM public.orders
            WHERE user_id = %s
            AND coupon_id = %s
            AND payment_status = 'SUCCESS'
        """, [user_id, coupon_id])

        if cursor.fetchone()[0] >= max_usage_per_user:
            return {"error": "You have already used this coupon the maximum number of times."}

    if is_first_order_only:

        cursor.execute("SELECT total_orders FROM public.users WHERE id = %s", [user_id])

        row = cursor.fetchone()

        if (row[0] or 0) > 0:
            return {"error": "This coupon is valid for first-time orders only."}

    if discount_type == "PERCENTAGE":
        discount_amount = subtotal * float(discount_value) / 100
        if maximum_discount_amount:
            discount_amount = min(discount_amount, float(maximum_discount_amount))
    else:
        discount_amount = float(discount_value)

    discount_amount = round(min(discount_amount, subtotal), 2)

    return {"coupon_id": coupon_id, "discount_amount": discount_amount}


def create_checkout_payment(validated_data, user_id):

    address_id = validated_data["address_id"]
    coupon_code = validated_data.get("coupon_code")

    with connection.cursor() as cursor:

        # 1. Account email (shipping name/mobile come from the address instead)
        cursor.execute("""
            SELECT email
            FROM public.users
            WHERE id = %s
            AND is_deleted = FALSE
            AND is_active = TRUE
        """, [user_id])

        user_row = cursor.fetchone()

        if not user_row:
            return {"message": "User not found."}, 404

        customer_email = user_row[0]

        # 2. Saved address (must belong to the authenticated user)
        cursor.execute("""
            SELECT
                full_name, mobile, address_line_1, address_line_2,
                landmark, city, state, country, pincode
            FROM public.addresses
            WHERE id = %s
            AND user_id = %s
            AND is_deleted = FALSE
        """, [address_id, user_id])

        address_row = cursor.fetchone()

        if not address_row:
            return {"message": "Address not found."}, 404

        (
            customer_name,
            customer_mobile,
            address_line_1,
            address_line_2,
            landmark,
            city,
            state,
            country,
            pincode
        ) = address_row

        # 3. Cart items, priced from the DB (never trust client-supplied prices)
        cursor.execute("""
            SELECT
                pvs.id AS variant_size_id,
                pvs.size,
                pvs.stock_quantity,
                v.id AS variant_id,
                v.color,
                v.mrp,
                v.selling_price,
                p.id AS product_id,
                p.name AS product_name,
                ci.quantity
            FROM public.cart_items ci
            JOIN public.product_variant_sizes pvs ON pvs.id = ci.variant_size_id
            JOIN public.product_variants v ON v.id = pvs.variant_id
            JOIN public.products p ON p.id = v.product_id
            WHERE ci.user_id = %s
            AND ci.is_deleted = FALSE
            AND ci.is_active = TRUE
        """, [user_id])

        cart_rows = cursor.fetchall()

        if not cart_rows:
            return {"message": "Your cart is empty."}, 400

        items = []
        insufficient_stock = []
        subtotal = 0.0

        for (
            variant_size_id, size, stock_quantity, variant_id, color,
            mrp, selling_price, product_id, product_name, quantity
        ) in cart_rows:

            if quantity > stock_quantity:
                insufficient_stock.append({
                    "product_name": product_name,
                    "size": size,
                    "color": color,
                    "requested": quantity,
                    "available": stock_quantity
                })
                continue

            mrp = float(mrp)
            selling_price = float(selling_price)
            total_amount = round(selling_price * quantity, 2)
            subtotal += total_amount

            items.append({
                "product_id": product_id,
                "variant_id": variant_id,
                "product_name": product_name,
                "size": size,
                "color": color,
                "quantity": quantity,
                "mrp": mrp,
                "selling_price": selling_price,
                "total_amount": total_amount
            })

        if insufficient_stock:
            return {
                "message": "Some items in your cart don't have enough stock.",
                "data": {"insufficient_stock": insufficient_stock}
            }, 400

        subtotal = round(subtotal, 2)

        # 4. Coupon (optional)
        coupon_id = None
        discount_amount = 0.0

        if coupon_code:

            coupon_result = _validate_coupon(cursor, coupon_code, user_id, subtotal)

            if "error" in coupon_result:
                return {"message": coupon_result["error"]}, 400

            coupon_id = coupon_result["coupon_id"]
            discount_amount = coupon_result["discount_amount"]

        grand_total = round(subtotal - discount_amount, 2)

        # 5. Insert order
        order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"

        cursor.execute("""
            INSERT INTO public.orders (
                order_number, user_id, customer_name, customer_email, customer_mobile,
                address_line_1, address_line_2, landmark, city, state, country, pincode,
                subtotal, discount_amount, shipping_amount, tax_amount, grand_total,
                coupon_id, payment_method, payment_status, order_status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,%s,%s,'RAZORPAY','PENDING','PLACED')
            RETURNING id;
        """, [
            order_number, user_id, customer_name, customer_email, customer_mobile,
            address_line_1, address_line_2, landmark, city, state, country, pincode,
            subtotal, discount_amount, grand_total, coupon_id
        ])

        order_id = cursor.fetchone()[0]

        # 6. Insert order items
        for item in items:

            cursor.execute("""
                INSERT INTO public.order_items (
                    order_id, product_id, variant_id, product_name, size, color,
                    quantity, mrp, selling_price, total_amount
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                order_id, item["product_id"], item["variant_id"], item["product_name"],
                item["size"], item["color"], item["quantity"], item["mrp"],
                item["selling_price"], item["total_amount"]
            ])

        # 7. Razorpay order
        razorpay_order = client.order.create({
            "amount": int(round(grand_total * 100)),
            "currency": "INR",
            "receipt": order_number,
            "payment_capture": 1
        })

        # 8. Insert payment row
        cursor.execute("""
            INSERT INTO public.payments (
                order_id,
                transaction_amount,
                razorpay_order_id,
                payment_status
            )
            VALUES (%s,%s,%s,'PENDING')
        """, [
            order_id,
            grand_total,
            razorpay_order["id"]
        ])

        connection.commit()

    return {
        "order_id": order_id,
        "razorpay_order_id": razorpay_order["id"],
        "amount": int(round(grand_total * 100)),
        "currency": "INR",
        "key": settings.RAZORPAY_KEY_ID
    }, 201



class _CheckoutAborted(Exception):
    """Raised to unwind the COD transaction.atomic() block with a specific response."""

    def __init__(self, payload, status_code):
        self.payload = payload
        self.status_code = status_code


def create_cod_order(validated_data, user_id):

    address_id = validated_data["address_id"]
    coupon_code = validated_data.get("coupon_code")

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:

                # 1. Account
                cursor.execute("""
                    SELECT email
                    FROM public.users
                    WHERE id = %s
                    AND is_deleted = FALSE
                    AND is_active = TRUE
                """, [user_id])

                user_row = cursor.fetchone()

                if not user_row:
                    raise _CheckoutAborted({"message": "User not found."}, 404)

                customer_email = user_row[0]

                # 2. Saved address (must belong to the authenticated user)
                cursor.execute("""
                    SELECT
                        full_name, mobile, address_line_1, address_line_2,
                        landmark, city, state, country, pincode
                    FROM public.addresses
                    WHERE id = %s
                    AND user_id = %s
                    AND is_deleted = FALSE
                """, [address_id, user_id])

                address_row = cursor.fetchone()

                if not address_row:
                    raise _CheckoutAborted({"message": "Address not found."}, 404)

                (
                    customer_name,
                    customer_mobile,
                    address_line_1,
                    address_line_2,
                    landmark,
                    city,
                    state,
                    country,
                    pincode
                ) = address_row

                # 3a. Cart items, priced from the DB. Plain read (no lock yet —
                # Postgres won't allow FOR UPDATE on the nullable side of these
                # outer joins) just to work out which cart rows still resolve to
                # a live, active size/variant/product.
                cursor.execute("""
                    SELECT
                        ci.id AS cart_item_id,
                        ci.quantity,
                        pvs.id AS variant_size_id,
                        pvs.size,
                        pvs.is_active AS size_active,
                        pvs.is_deleted AS size_deleted,
                        v.id AS variant_id,
                        v.color,
                        v.mrp,
                        v.selling_price,
                        v.is_active AS variant_active,
                        v.is_deleted AS variant_deleted,
                        p.id AS product_id,
                        p.name AS product_name,
                        p.is_active AS product_active,
                        p.is_deleted AS product_deleted
                    FROM public.cart_items ci
                    LEFT JOIN public.product_variant_sizes pvs ON pvs.id = ci.variant_size_id
                    LEFT JOIN public.product_variants v ON v.id = pvs.variant_id
                    LEFT JOIN public.products p ON p.id = v.product_id
                    WHERE ci.user_id = %s
                    AND ci.is_deleted = FALSE
                    AND ci.is_active = TRUE
                """, [user_id])

                cart_rows = cursor.fetchall()

                if not cart_rows:
                    raise _CheckoutAborted({"message": "Your cart is empty."}, 400)

                candidates = []
                unavailable_items = []

                for (
                    cart_item_id, quantity, variant_size_id, size,
                    size_active, size_deleted, variant_id, color, mrp, selling_price,
                    variant_active, variant_deleted, product_id, product_name,
                    product_active, product_deleted
                ) in cart_rows:

                    # The size (or its variant/product) was removed or deactivated
                    # by an admin after this item was added to the cart.
                    if (
                        variant_size_id is None
                        or size_deleted or not size_active
                        or variant_deleted or not variant_active
                        or product_deleted or not product_active
                    ):
                        unavailable_items.append({
                            "cart_item_id": cart_item_id,
                            "product_name": product_name,
                            "size": size,
                            "color": color
                        })
                        continue

                    candidates.append({
                        "variant_size_id": variant_size_id,
                        "product_id": product_id,
                        "variant_id": variant_id,
                        "product_name": product_name,
                        "size": size,
                        "color": color,
                        "quantity": quantity,
                        "mrp": float(mrp),
                        "selling_price": float(selling_price)
                    })

                if unavailable_items:
                    raise _CheckoutAborted({
                        "message": "Some items in your cart are no longer available. Please review your cart.",
                        "data": {"unavailable_items": unavailable_items}
                    }, 400)

                # 3b. Lock the actual stock rows (a plain, non-outer-joined SELECT,
                # so FOR UPDATE is allowed here) and re-check stock against that
                # locked snapshot — this is what actually prevents a concurrent
                # order from overselling the same size.
                cursor.execute("""
                    SELECT id, stock_quantity
                    FROM public.product_variant_sizes
                    WHERE id = ANY(%s)
                    FOR UPDATE
                """, [[c["variant_size_id"] for c in candidates]])

                locked_stock = dict(cursor.fetchall())

                items = []
                insufficient_stock = []
                subtotal = 0.0

                for candidate in candidates:

                    available = locked_stock.get(candidate["variant_size_id"], 0)

                    if candidate["quantity"] > available:
                        insufficient_stock.append({
                            "product_name": candidate["product_name"],
                            "size": candidate["size"],
                            "color": candidate["color"],
                            "requested": candidate["quantity"],
                            "available": available
                        })
                        continue

                    total_amount = round(candidate["selling_price"] * candidate["quantity"], 2)
                    subtotal += total_amount

                    items.append({**candidate, "total_amount": total_amount})

                if insufficient_stock:
                    raise _CheckoutAborted({
                        "message": "Some items in your cart don't have enough stock.",
                        "data": {"insufficient_stock": insufficient_stock}
                    }, 400)

                subtotal = round(subtotal, 2)

                # 4. Coupon (optional)
                coupon_id = None
                discount_amount = 0.0

                if coupon_code:

                    coupon_result = _validate_coupon(cursor, coupon_code, user_id, subtotal)

                    if "error" in coupon_result:
                        raise _CheckoutAborted({"message": coupon_result["error"]}, 400)

                    coupon_id = coupon_result["coupon_id"]
                    discount_amount = coupon_result["discount_amount"]

                grand_total = round(subtotal - discount_amount, 2)

                # 5. Insert order. COD is confirmed immediately — there's no
                # gateway round-trip and no later webhook to reconcile stock,
                # so this whole block commits or rolls back as one unit.
                order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"

                cursor.execute("""
                    INSERT INTO public.orders (
                        order_number, user_id, customer_name, customer_email, customer_mobile,
                        address_line_1, address_line_2, landmark, city, state, country, pincode,
                        subtotal, discount_amount, shipping_amount, tax_amount, grand_total,
                        coupon_id, payment_method, payment_status, order_status,
                        ordered_at, created_at, updated_at
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,0,0,%s,
                        %s,'COD','PENDING','PLACED',
                        NOW(),NOW(),NOW()
                    )
                    RETURNING id;
                """, [
                    order_number, user_id, customer_name, customer_email, customer_mobile,
                    address_line_1, address_line_2, landmark, city, state, country, pincode,
                    subtotal, discount_amount, grand_total, coupon_id
                ])

                order_id = cursor.fetchone()[0]

                # 6. Order items + stock decrement. The rows are already locked
                # (step 3), but the WHERE guard is kept as a belt-and-braces check.
                for item in items:

                    cursor.execute("""
                        INSERT INTO public.order_items (
                            order_id, product_id, variant_id, product_name, size, color,
                            quantity, mrp, selling_price, total_amount, created_at, updated_at
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                    """, [
                        order_id, item["product_id"], item["variant_id"], item["product_name"],
                        item["size"], item["color"], item["quantity"], item["mrp"],
                        item["selling_price"], item["total_amount"]
                    ])

                    cursor.execute("""
                        UPDATE public.product_variant_sizes
                        SET stock_quantity = stock_quantity - %s
                        WHERE id = %s
                        AND stock_quantity >= %s
                        RETURNING stock_quantity
                    """, [item["quantity"], item["variant_size_id"], item["quantity"]])

                    if cursor.fetchone() is None:
                        raise _CheckoutAborted({
                            "message": f"{item['product_name']} ({item['color']}, {item['size']}) sold out just now. Please update your cart and try again."
                        }, 409)

                # 7. Purchased items no longer belong in the cart.
                cursor.execute("""
                    UPDATE public.cart_items
                    SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
                    WHERE user_id = %s
                    AND variant_size_id = ANY(%s)
                    AND is_deleted = FALSE
                """, [user_id, [item["variant_size_id"] for item in items]])

                # 8. The order is confirmed now even though cash hasn't been
                # collected yet, so a one-time coupon or first-order eligibility
                # can't be replayed by placing several COD orders back to back.
                cursor.execute("""
                    UPDATE public.users
                    SET
                        total_orders = COALESCE(total_orders, 0) + 1,
                        last_order_at = NOW()
                    WHERE id = %s
                """, [user_id])

                if coupon_id:
                    cursor.execute("""
                        UPDATE public.coupons
                        SET used_count = COALESCE(used_count, 0) + 1
                        WHERE id = %s
                    """, [coupon_id])

    except _CheckoutAborted as e:
        return e.payload, e.status_code

    return {
        "message": "Order placed successfully. Pay with cash on delivery.",
        "data": {
            "order_id": order_id,
            "order_number": order_number,
            "payment_method": "COD",
            "payment_status": "PENDING",
            "order_status": "PLACED",
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "grand_total": grand_total
        }
    }, 201



def verify_payment(validated_data, user_id):

    generated_signature = hmac.new(
        key=bytes(settings.RAZORPAY_KEY_SECRET, "utf-8"),
        msg=bytes(
            f"{validated_data['razorpay_order_id']}|{validated_data['razorpay_payment_id']}",
            "utf-8"
        ),
        digestmod=hashlib.sha256
    ).hexdigest()

    if generated_signature == validated_data["razorpay_signature"]:
        return {"message": "Payment verified successfully."}, 200

    return {"message": "Invalid signature."}, 400


def razorpay_webhook_handler(request):

    payload = request.body.decode("utf-8")

    signature = request.headers.get("X-Razorpay-Signature")

    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # ❌ MUST return Response, not tuple
    if expected_signature != signature:
        return Response(
            {"message": "Invalid signature"},
            status=400
        )

    data = json.loads(payload)

    payment = data["payload"]["payment"]["entity"]

    razorpay_order_id = payment["order_id"]
    razorpay_payment_id = payment["id"]
    status_value = payment["status"]

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT p.id, p.order_id, o.user_id, o.grand_total, o.payment_status, o.coupon_id
            FROM public.payments p
            JOIN public.orders o ON o.id = p.order_id
            WHERE p.razorpay_order_id=%s
        """, [razorpay_order_id])

        row = cursor.fetchone()

        if not row:
            return Response(
                {"message": "Payment not found"},
                status=200
            )

        payment_id, order_id, user_id, grand_total, existing_payment_status, coupon_id = row

        new_payment_status = "SUCCESS" if status_value == "captured" else "FAILED"

        cursor.execute("""
            UPDATE public.payments
            SET
                razorpay_payment_id=%s,
                payment_status=%s,
                gateway_response=%s,
                paid_at=NOW()
            WHERE id=%s
        """, [
            razorpay_payment_id,
            new_payment_status,
            json.dumps(data),
            payment_id
        ])

        cursor.execute("""
            UPDATE public.orders
            SET payment_status=%s
            WHERE id=%s
        """, [
            new_payment_status,
            order_id
        ])

        # Everything below only happens on the transition into SUCCESS,
        # so repeated webhook deliveries don't double-apply.
        if new_payment_status == "SUCCESS" and existing_payment_status != "SUCCESS":

            cursor.execute("""
                UPDATE public.users
                SET
                    total_orders = COALESCE(total_orders, 0) + 1,
                    total_spent = COALESCE(total_spent, 0) + %s,
                    last_order_at = NOW()
                WHERE id=%s
            """, [grand_total, user_id])

            if coupon_id:
                cursor.execute("""
                    UPDATE public.coupons
                    SET used_count = COALESCE(used_count, 0) + 1
                    WHERE id=%s
                """, [coupon_id])

            # Decrement stock for the purchased sizes.
            cursor.execute("""
                UPDATE public.product_variant_sizes pvs
                SET stock_quantity = pvs.stock_quantity - oi.quantity
                FROM public.order_items oi
                WHERE oi.order_id = %s
                AND pvs.variant_id = oi.variant_id
                AND pvs.size = oi.size
            """, [order_id])

            # Purchased items no longer belong in the cart.
            cursor.execute("""
                UPDATE public.cart_items ci
                SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
                FROM public.order_items oi
                JOIN public.product_variant_sizes pvs
                    ON pvs.variant_id = oi.variant_id AND pvs.size = oi.size
                WHERE oi.order_id = %s
                AND ci.user_id = %s
                AND ci.variant_size_id = pvs.id
                AND ci.is_deleted = FALSE
            """, [order_id, user_id])

    return Response(
        {"message": "Webhook processed"},
        status=200
    )