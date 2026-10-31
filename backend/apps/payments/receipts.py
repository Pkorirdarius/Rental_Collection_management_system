import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def money(value) -> str:
    return f"KES {Decimal(value):,.2f}"


def build_receipt_pdf(payment, receipt) -> bytes:
    from apps.ledger.services import lease_balance

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Receipt {receipt.number}",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#4b5563"),
        )
    )
    org = payment.organization
    lease = payment.lease
    balance = lease_balance(lease) if lease else Decimal("0.00")

    story = [
        Paragraph(f"<b>{org.name}</b>", styles["Title"]),
        Paragraph(
            f"{org.county or ''} {org.phone or ''} &nbsp;|&nbsp; {org.email or ''}",
            styles["Small"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("<b>OFFICIAL RENT RECEIPT</b>", styles["Heading2"]),
        Spacer(1, 4 * mm),
    ]

    rows = [
        ["Receipt number", receipt.number],
        ["Date", receipt.issued_at.strftime("%d %b %Y %H:%M")],
        ["Tenant", payment.tenant.full_name if payment.tenant else "-"],
        ["Property / unit", f"{lease.unit.property.name} / {lease.unit.code}" if lease else "-"],
        ["Payment method", payment.get_method_display()],
        ["Reference", payment.reference or "-"],
        ["Received by", payment.received_by.full_name if payment.received_by else "-"],
    ]
    table = Table(rows, colWidths=[45 * mm, 120 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    story += [table, Spacer(1, 8 * mm)]

    amount_table = Table(
        [
            ["Amount received", money(payment.amount)],
            ["Outstanding balance after payment", money(balance)],
        ],
        colWidths=[80 * mm, 60 * mm],
    )
    amount_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#16a34a")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story += [amount_table, Spacer(1, 10 * mm)]
    if payment.notes:
        story += [Paragraph(f"<b>Note:</b> {payment.notes}", styles["Normal"]), Spacer(1, 6 * mm)]
    story += [
        Paragraph(
            "This is a system-generated receipt. Financial records are immutable; "
            "corrections are made through reversal entries only.",
            styles["Small"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(f"Payment ID: {payment.id}", styles["Small"]),
    ]
    doc.build(story)
    return buffer.getvalue()
