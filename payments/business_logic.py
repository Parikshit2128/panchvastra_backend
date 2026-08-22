import uuid
from django.db import connection, transaction
from django.conf import settings
from rest_framework.response import Response

from .services.razorpay_client import client
import json
import hmac
import hashlib


def create_checkout_payment(validated_data, user_id):

    with connection.cursor() as cursor:

        # 1. Create order number
        order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"

        # 2. Calculate total
        subtotal = 0

        for item in validated_data["items"]:
            subtotal += float(item["selling_price"]) * int(item["quantity"])

        grand_total = subtotal

        # 3. Insert order
        cursor.execute("""
            INSERT INTO public.orders (
                order_number,
                user_id,
                customer_name,
                customer_email,
                customer_mobile,
                address_line_1,
                address_line_2,
                landmark,
                city,
                state,
                pincode,
                subtotal,
                grand_total,
                payment_status,
                order_status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING','PLACED')
            RETURNING id;
        """, [
            order_number,
            user_id,
            validated_data["customer_name"],
            validated_data.get("customer_email"),
            validated_data["customer_mobile"],
            validated_data["address_line_1"],
            validated_data.get("address_line_2"),
            validated_data.get("landmark"),
            validated_data["city"],
            validated_data["state"],
            validated_data["pincode"],
            subtotal,
            grand_total
        ])

        order_id = cursor.fetchone()[0]

        # 4. Insert order items
        for item in validated_data["items"]:

            cursor.execute("""
                INSERT INTO public.order_items (
                    order_id,
                    product_id,
                    product_name,
                    size,
                    color,
                    quantity,
                    mrp,
                    selling_price,
                    total_amount
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                order_id,
                item["product_id"],
                item["product_name"],
                item.get("size"),
                item.get("color"),
                item["quantity"],
                item.get("mrp"),
                item["selling_price"],
                float(item["selling_price"]) * int(item["quantity"])
            ])

        # 5. Razorpay order
        razorpay_order = client.order.create({
            "amount": int(grand_total * 100),
            "currency": "INR",
            "receipt": order_number,
            "payment_capture": 1
        })

        # 6. Insert payment row
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

    return {
        "order_id": order_id,
        "razorpay_order_id": razorpay_order["id"],
        "amount": int(grand_total * 100),
        "currency": "INR",
        "key": settings.RAZORPAY_KEY_ID
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
            SELECT p.id, p.order_id, o.user_id, o.grand_total, o.payment_status
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

        payment_id, order_id, user_id, grand_total, existing_payment_status = row

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

        # Update user order stats only on the transition into SUCCESS,
        # so repeated webhook deliveries don't double-count.
        if new_payment_status == "SUCCESS" and existing_payment_status != "SUCCESS":
            cursor.execute("""
                UPDATE public.users
                SET
                    total_orders = COALESCE(total_orders, 0) + 1,
                    total_spent = COALESCE(total_spent, 0) + %s,
                    last_order_at = NOW()
                WHERE id=%s
            """, [grand_total, user_id])

    return Response(
        {"message": "Webhook processed"},
        status=200
    )