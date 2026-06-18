"""
VESTRA Rent Receipt Service — PDF generation for rent payment receipts.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("vestra")

try:
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


async def generate_rent_receipt_pdf(
    db: AsyncSession,
    payment_id: int,
    unit_id: int,
) -> Optional[bytes]:
    """Generate a branded A5 rent receipt PDF. Returns bytes or None if unavailable."""
    if not REPORTLAB_AVAILABLE:
        return None

    from app.models.rental import RentPayment, RentalUnit, Tenant

    # Load payment
    pay_result = await db.execute(
        select(RentPayment).where(RentPayment.id == payment_id, RentPayment.unit_id == unit_id)
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        return None

    # Load unit and tenant
    unit_result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = unit_result.scalar_one_or_none()

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == payment.tenant_id))
    tenant = tenant_result.scalar_one_or_none()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A5, leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=10*mm, bottomMargin=10*mm)

    styles = getSampleStyleSheet()
    story = []

    # Header
    story.append(Paragraph("<b>VESTRA</b> Rent Receipt",
                   ParagraphStyle('h', parent=styles['Heading1'], fontSize=16,
                                  textColor=HexColor("#10b981"), alignment=TA_CENTER)))
    story.append(Paragraph(f"Receipt #RCP-{payment.id:06d}",
                   ParagraphStyle('sub', parent=styles['Normal'], fontSize=9,
                                  textColor=HexColor("#6b7280"), alignment=TA_CENTER)))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#10b981"), spaceAfter=5*mm))

    # Receipt data
    data = [
        ["Receipt Number", f"RCP-{payment.id:06d}"],
        ["Date", payment.paid_date.strftime("%d %B %Y") if payment.paid_date else "-"],
        ["Month", payment.month],
        ["", ""],
        ["Landlord", unit.landlord_id if unit else "-"],
        ["Tenant", tenant.full_name if tenant else "-"],
        ["Phone", tenant.phone if tenant else "-"],
        ["Unit", unit.name if unit else "-"],
        ["", ""],
        ["Rent Amount", f"KES {float(payment.amount_kes or 0):,.2f}"],
        ["Amount Paid", f"KES {float(payment.amount_paid_kes or 0):,.2f}"],
        ["Late Fee", f"KES {float(payment.late_fee_kes or 0):,.2f}"],
        ["Payment Status", payment.status.value.upper()],
        ["", ""],
        ["M-Pesa Ref", payment.mpesa_receipt or "N/A"],
    ]

    t = Table(data, colWidths=[55*mm, 75*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), HexColor("#374151")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, -2), (-1, -2), 1, HexColor("#10b981")),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#d1d5db")))
    story.append(Paragraph(
        "This is a computer-generated receipt from Vestra.<br/>"
        "Vestra.co.ke — Africa's Most Trusted Property Platform",
        ParagraphStyle('foot', parent=styles['Normal'], fontSize=7,
                       textColor=HexColor("#9ca3af"), alignment=TA_CENTER)
    ))

    try:
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        logger.error('{"event":"receipt_pdf_failed","error":"%s"}', str(e))
        return None
