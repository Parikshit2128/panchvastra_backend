"""PDF invoice for a single order.

Deliberately built from the same dict get_order_detail already returns, so
the invoice can never disagree with what the order screens show. ReportLab's
platypus flowables handle the page breaks for an order with many items.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle
)


# The rupee glyph is missing from ReportLab's built-in Type 1 fonts, so it
# renders as a black box. "Rs." is used instead rather than shipping and
# registering a TTF purely for one character.
CURRENCY = "Rs."

INK = colors.HexColor("#111111")
MUTED = colors.HexColor("#666666")
RULE = colors.HexColor("#DDDDDD")


def _money(value):
    return f"{CURRENCY} {float(value or 0):,.2f}"


def _format_datetime(value):
    if not value:
        return "-"
    return value.strftime("%d %b %Y, %I:%M %p")


def _format_date(value):
    if not value:
        return "-"
    return value.strftime("%d %b %Y")


def build_invoice_pdf(order):
    """Render one order dict (get_order_detail's "data") to PDF bytes."""

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Invoice {order.get('order_number', '')}",
        author="Panchvastra"
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        alignment=0,
        textColor=INK,
        spaceAfter=2
    )

    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=MUTED
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=INK
    )

    right_style = ParagraphStyle(
        "Right",
        parent=body_style,
        alignment=TA_RIGHT
    )

    story = []

    story.append(Paragraph("PANCHVASTRA", title_style))
    story.append(Paragraph("Tax Invoice", label_style))
    story.append(Spacer(1, 10))

    address = order.get("address") or {}

    billed_to = "<br/>".join(
        part for part in [
            address.get("customer_name"),
            address.get("address_line_1"),
            address.get("address_line_2"),
            address.get("landmark"),
            " ".join(
                part for part in [
                    address.get("city"),
                    address.get("state"),
                    str(address.get("pincode") or "")
                ] if part
            ).strip(),
            address.get("country"),
            address.get("customer_mobile"),
            address.get("customer_email")
        ] if part
    )

    meta_rows = [
        ["Invoice No.", order.get("order_number") or "-"],
        ["Order Date", _format_datetime(order.get("ordered_at"))],
        ["Payment", f"{order.get('payment_method') or '-'} ({order.get('payment_status') or '-'})"],
        ["Transaction ID", order.get("transaction_id") or "-"],
        ["Order Status", order.get("status_label") or order.get("order_status") or "-"]
    ]

    meta_table = Table(
        [
            [Paragraph(label, label_style), Paragraph(str(value), body_style)]
            for label, value in meta_rows
        ],
        colWidths=[28 * mm, 50 * mm]
    )

    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0)
    ]))

    header = Table(
        [[
            [
                Paragraph("BILLED TO", label_style),
                Spacer(1, 3),
                Paragraph(billed_to or "-", body_style)
            ],
            meta_table
        ]],
        colWidths=[94 * mm, 80 * mm]
    )

    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0)
    ]))

    story.append(header)
    story.append(Spacer(1, 16))

    item_rows = [[
        Paragraph("ITEM", label_style),
        Paragraph("SKU", label_style),
        Paragraph("QTY", label_style),
        Paragraph("PRICE", label_style),
        Paragraph("TOTAL", label_style)
    ]]

    for item in order.get("items") or []:

        variant = " / ".join(
            part for part in [item.get("color"), item.get("size")] if part
        )

        name = item.get("product_name") or "-"

        if variant:
            name = f"{name}<br/><font size=8 color='#666666'>{variant}</font>"

        item_rows.append([
            Paragraph(name, body_style),
            Paragraph(item.get("sku") or "-", body_style),
            Paragraph(str(item.get("quantity") or 0), right_style),
            Paragraph(_money(item.get("selling_price")), right_style),
            Paragraph(_money(item.get("total_amount")), right_style)
        ])

    items_table = Table(
        item_rows,
        colWidths=[72 * mm, 32 * mm, 14 * mm, 28 * mm, 28 * mm],
        repeatRows=1
    )

    items_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT")
    ]))

    story.append(items_table)
    story.append(Spacer(1, 12))

    summary = order.get("price_summary") or {}

    discount = float(summary.get("discount_amount") or 0)

    summary_rows = [
        ("Subtotal", _money(summary.get("subtotal"))),
        # Shown as "- Rs. 499.00" rather than "Rs. -499.00", matching how the
        # order summary reads on screen.
        ("Discount", f"- {_money(discount)}" if discount else _money(0)),
        ("Shipping", _money(summary.get("shipping_amount"))),
        ("Tax", _money(summary.get("tax_amount")))
    ]

    summary_data = [
        [Paragraph(label, body_style), Paragraph(value, right_style)]
        for label, value in summary_rows
    ]

    summary_data.append([
        Paragraph("<b>Total Paid</b>", body_style),
        Paragraph(f"<b>{_money(summary.get('grand_total'))}</b>", right_style)
    ])

    summary_table = Table(summary_data, colWidths=[40 * mm, 34 * mm])

    summary_table.setStyle(TableStyle([
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, INK),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0)
    ]))

    wrapper = Table([["", summary_table]], colWidths=[100 * mm, 74 * mm])

    wrapper.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0)
    ]))

    story.append(wrapper)
    story.append(Spacer(1, 18))

    if order.get("expected_delivery_date"):
        story.append(Paragraph(
            f"Expected delivery: {_format_date(order['expected_delivery_date'])}",
            label_style
        ))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This is a computer generated invoice and does not require a signature.",
        label_style
    ))

    doc.build(story)

    return buffer.getvalue()
