"""
invoice_pdf.py — Generate PDF invoices for sales and repairs.
Shared by routes/sales.py and routes/repairs.py.
"""
import io, os, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _BIDI_AVAILABLE = True
except ImportError:
    _BIDI_AVAILABLE = False

# ── FONT REGISTRATION (Arabic + Latin Unicode support) ──────
_FONT_DIR = os.path.join(os.path.dirname(__file__), "static", "fonts")
_ARABIC_REGULAR = "NotoArabic"
_ARABIC_BOLD    = "NotoArabic-Bold"
_FONTS_REGISTERED = False

def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    try:
        pdfmetrics.registerFont(TTFont(_ARABIC_REGULAR, os.path.join(_FONT_DIR, "NotoSansArabic-Regular.ttf")))
        pdfmetrics.registerFont(TTFont(_ARABIC_BOLD, os.path.join(_FONT_DIR, "NotoSansArabic-Bold.ttf")))
    except Exception:
        pass  # Fall back to Helvetica if fonts missing; Arabic text just won't render (no crash)
    _FONTS_REGISTERED = True

_ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F]')

def shape_text(text):
    """
    Reshape and reorder Arabic text for correct visual rendering in PDFs.
    Leaves non-Arabic text untouched. Mixed text is shaped as a whole line,
    which is good enough for short labels (plate numbers, names) used here.
    """
    if not text or not _ARABIC_RE.search(text):
        return text, False
    if not _BIDI_AVAILABLE:
        return text, False
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped), True
    except Exception:
        return text, False

SHOP_NAME    = "Z-MOTO MANAGER"
SHOP_TAGLINE = "Moto Parts & Repairs — Tunisia"
ACCENT       = colors.HexColor("#ff4757")
DARK         = colors.HexColor("#1a1f2e")
GREY         = colors.HexColor("#6b7280")
LIGHT_BG     = colors.HexColor("#f4f5fb")

def _styles():
    _register_fonts()
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("ShopName", parent=ss["Heading1"], fontSize=20, textColor=DARK, spaceAfter=2))
    ss.add(ParagraphStyle("Tagline", parent=ss["Normal"], fontSize=9, textColor=GREY))
    ss.add(ParagraphStyle("InvoiceTitle", parent=ss["Heading2"], fontSize=16, textColor=ACCENT, alignment=TA_RIGHT))
    ss.add(ParagraphStyle("InvoiceMeta", parent=ss["Normal"], fontSize=9, textColor=GREY, alignment=TA_RIGHT))
    ss.add(ParagraphStyle("SectionLabel", parent=ss["Normal"], fontSize=8, textColor=GREY, spaceBefore=6))
    ss.add(ParagraphStyle("BodyBold", parent=ss["Normal"], fontSize=10, textColor=DARK, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=10, textColor=DARK))
    ss.add(ParagraphStyle("BodyAr", parent=ss["Normal"], fontSize=10, textColor=DARK, fontName=_ARABIC_REGULAR, alignment=TA_RIGHT))
    ss.add(ParagraphStyle("TotalLabel", parent=ss["Normal"], fontSize=12, textColor=DARK, alignment=TA_RIGHT, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("TotalValue", parent=ss["Normal"], fontSize=14, textColor=ACCENT, alignment=TA_RIGHT, fontName="Helvetica-Bold"))
    return ss

def _money(v):
    return f"{float(v or 0):.2f} TND"

def _payment_label(status):
    return {"paid": "PAID", "partial": "PARTIALLY PAID", "unpaid": "UNPAID"}.get(status, status.upper())

def _payment_color(status):
    return {"paid": colors.HexColor("#2ed573"), "partial": colors.HexColor("#ffa502"), "unpaid": colors.HexColor("#ff4757")}.get(status, GREY)

def _safe_line(text, ss):
    """
    Render a line of text that may contain Arabic safely as its own
    Paragraph using the Arabic-capable font when needed, otherwise
    plain Helvetica via the normal Body style. Returns a Paragraph.
    """
    shaped, is_arabic = shape_text(text)
    style = ss["BodyAr"] if is_arabic else ss["Body"]
    return Paragraph(shaped, style)


def build_invoice_pdf(*, invoice_number, doc_type, customer, line_items,
                       discount=0, total=0, amount_paid=0, payment_status="paid",
                       payment_method="cash", note="", staff="", created_at="", extra_info=None):
    """
    Build a PDF invoice and return it as bytes.

    doc_type: "Sale Invoice" or "Repair Invoice"
    customer: dict with name, phone, address (or None for walk-in)
    line_items: list of dicts: {description, qty, unit_price}
    extra_info: list of (label, value) tuples shown under the customer block
                (e.g. [("Vehicle", "Yamaha YBR 125"), ("Plate", "123 TUN 4567")])
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm, topMargin=18*mm, bottomMargin=18*mm
    )
    ss = _styles()
    story = []

    # ── HEADER ──
    header_data = [[
        Paragraph(f"<b>{SHOP_NAME}</b>", ss["ShopName"]),
        Paragraph(f"{doc_type}", ss["InvoiceTitle"]),
    ], [
        Paragraph(SHOP_TAGLINE, ss["Tagline"]),
        Paragraph(f"Invoice #: <b>{invoice_number}</b><br/>Date: {created_at}", ss["InvoiceMeta"]),
    ]]
    header_table = Table(header_data, colWidths=[100*mm, 70*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,0), 2),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", color=ACCENT, thickness=2))
    story.append(Spacer(1, 14))

    # ── CUSTOMER + STATUS BLOCK ──
    cust_paragraphs = [Paragraph("<b>Bill To</b>", ss["Body"])]
    if customer and customer.get("name"):
        cust_paragraphs.append(_safe_line(customer["name"], ss))
        if customer.get("phone"):
            cust_paragraphs.append(_safe_line(f"Tel: {customer['phone']}", ss))
        if customer.get("address"):
            cust_paragraphs.append(_safe_line(customer["address"], ss))
    else:
        cust_paragraphs.append(Paragraph("Walk-in Customer", ss["Body"]))

    right_paragraphs = [
        Paragraph(f"<b>Staff:</b> {staff or '—'}", ss["Body"]),
        Paragraph(f"<b>Payment Method:</b> {payment_method.replace('_',' ').title()}", ss["Body"]),
    ]
    if extra_info:
        for label, value in extra_info:
            if value:
                shaped, is_ar = shape_text(str(value))
                right_paragraphs.append(Paragraph(f"<b>{label}:</b> {shaped}", ss["BodyAr"] if is_ar else ss["Body"]))

    # Stack each line as its own mini-table row so Arabic and Latin lines
    # can each use the correct font without breaking Paragraph's single-style limitation.
    left_stack  = Table([[p] for p in cust_paragraphs], colWidths=[90*mm])
    right_stack = Table([[p] for p in right_paragraphs], colWidths=[80*mm])
    for t in (left_stack, right_stack):
        t.setStyle(TableStyle([
            ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 1), ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ]))

    info_table = Table([[left_stack, right_stack]], colWidths=[90*mm, 80*mm])
    info_table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(info_table)
    story.append(Spacer(1, 16))

    # ── LINE ITEMS TABLE ──
    table_data = [["#", "Description", "Qty", "Unit Price", "Subtotal"]]
    for i, item in enumerate(line_items, 1):
        qty   = item.get("qty", 1)
        price = item.get("unit_price", 0)
        sub   = qty * price
        desc_shaped, desc_is_ar = shape_text(item.get("description", ""))
        desc_cell = Paragraph(desc_shaped, ss["BodyAr"] if desc_is_ar else ss["Body"])
        table_data.append([
            str(i), desc_cell, str(qty), _money(price), _money(sub)
        ])

    items_table = Table(table_data, colWidths=[10*mm, 90*mm, 15*mm, 30*mm, 30*mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), DARK),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ALIGN",      (2,0), (-1,-1), "RIGHT"),
        ("ALIGN",      (0,0), (0,-1), "CENTER"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT_BG]),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#dde1ec")),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 14))

    # ── TOTALS BLOCK ──
    subtotal = sum(item.get("qty",1) * item.get("unit_price",0) for item in line_items)
    balance_due = max(total - amount_paid, 0)

    totals_rows = [["Subtotal", _money(subtotal)]]
    if discount:
        totals_rows.append(["Discount", f"-{_money(discount)}"])
    totals_rows.append(["TOTAL", _money(total)])
    totals_rows.append(["Amount Paid", _money(amount_paid)])
    totals_rows.append(["Balance Due", _money(balance_due)])

    totals_table = Table(totals_rows, colWidths=[40*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("FONTNAME", (0,-3), (-1,-3), "Helvetica-Bold"),
        ("FONTSIZE", (0,-3), (-1,-3), 12),
        ("TEXTCOLOR", (0,-3), (-1,-3), ACCENT),
        ("LINEABOVE", (0,-3), (-1,-3), 1, DARK),
        ("TOPPADDING", (0,-3), (-1,-3), 6),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0,-1), (-1,-1), colors.HexColor("#ff4757") if balance_due > 0 else colors.HexColor("#2ed573")),
    ]))

    # Right-align the totals block on the page
    wrapper = Table([[Spacer(1,1), totals_table]], colWidths=[105*mm, 75*mm])
    wrapper.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(wrapper)
    story.append(Spacer(1, 10))

    # ── PAYMENT STATUS BADGE ──
    status_para = Paragraph(
        f'<font color="{_payment_color(payment_status).hexval()}"><b>{_payment_label(payment_status)}</b></font>',
        ss["Body"]
    )
    story.append(status_para)
    story.append(Spacer(1, 10))

    # ── NOTE ──
    if note:
        note_shaped, note_is_ar = shape_text(note)
        note_style = ss["BodyAr"] if note_is_ar else ss["Body"]
        story.append(Paragraph(f"<b>Note:</b> {note_shaped}" if not note_is_ar else note_shaped, note_style))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dde1ec"), thickness=1))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Thank you for your business!", ss["Tagline"]))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
