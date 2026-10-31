import io
from datetime import datetime

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_excel(title: str, headers: list[str], rows: list[list]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title[:31]
    sheet.append(headers)
    header_fill = PatternFill("solid", fgColor="166534")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        sheet.append(row)
    for index, header in enumerate(headers, start=1):
        width = max([len(str(header))] + [len(str(row[index - 1])) for row in rows if len(row) >= index])
        sheet.column_dimensions[get_column_letter(index)].width = min(max(width + 4, 12), 45)
    sheet.freeze_panes = "A2"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_report_pdf(
    organization, title: str, headers: list[str], rows: list[list], subtitle: str = ""
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=title,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"<b>{organization.name}</b>", styles["Title"]),
        Paragraph(title, styles["Heading2"]),
    ]
    if subtitle:
        story.append(Paragraph(subtitle, styles["Normal"]))
    story.append(
        Paragraph(
            f"Generated {timezone.localtime():%d %b %Y %H:%M} EAT",
            styles["Italic"],
        )
    )
    story.append(Spacer(1, 6 * mm))

    data = [headers] + [[str(cell) for cell in row] for row in rows]
    available = landscape(A4)[0] - 28 * mm
    col_width = available / max(len(headers), 1)
    table = Table(data, colWidths=[col_width] * len(headers), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#166534")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def build_tenant_statement_pdf(tenant) -> bytes:
    from apps.ledger.services import tenant_statement

    statement = tenant_statement(tenant)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Statement {tenant.full_name}",
    )
    styles = getSampleStyleSheet()
    org = tenant.organization
    story = [
        Paragraph(f"<b>{org.name}</b>", styles["Title"]),
        Paragraph("TENANT STATEMENT", styles["Heading2"]),
        Paragraph(f"{tenant.full_name} &nbsp;|&nbsp; {tenant.phone}", styles["Normal"]),
        Paragraph(f"Generated {timezone.localtime():%d %b %Y %H:%M} EAT", styles["Italic"]),
        Spacer(1, 6 * mm),
    ]
    for lease in statement["leases"]:
        story.append(
            Paragraph(
                f"<b>{lease['property']} / {lease['unit']}</b> &nbsp; "
                f"Balance KES {lease['balance']} &nbsp; Status {lease['status']}",
                styles["Heading3"],
            )
        )
        data = [["Date", "Description", "Debit", "Credit", "Balance"]]
        for entry in lease["entries"]:
            data.append(
                [
                    entry["date"],
                    entry["description"][:60],
                    entry["debit"],
                    entry["credit"],
                    entry["balance"],
                ]
            )
        table = Table(data, colWidths=[24 * mm, 80 * mm, 22 * mm, 22 * mm, 24 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#166534")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story += [table, Spacer(1, 6 * mm)]
    story.append(
        Paragraph(
            f"<b>Total outstanding: KES {statement['total_balance']}</b>",
            styles["Heading3"],
        )
    )
    doc.build(story)
    return buffer.getvalue()
