"""
VESTRA Verification Report Service — PDF generation for paid trust reports.
Uses ReportLab for production-quality branded PDFs with:
- VESTRA header/footer with branding
- Trust Score gauge (0-100 visual)
- Fraud risk flags and analysis
- Price reasonableness comparison
- Ownership confidence level
- AI-generated summary
- QR code linking to live report
"""
from __future__ import annotations

import io
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

# Lazy-import reportlab to avoid import errors if not installed
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, black, white, grey
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, PageBreak, HRFlowable
    )
    from reportlab.graphics.shapes import Drawing, Rect, String, Group
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning('{"event":"reportlab_not_installed","message":"PDF reports disabled. Install reportlab: pip install reportlab"}')


# ── Brand colors ─────────────────────────────────────────────────────────────────

VESTRA_GREEN = HexColor("#10b981")
VESTRA_DARK = HexColor("#064e3b")
VESTRA_GREY = HexColor("#6b7280")
VESTRA_LIGHT_BG = HexColor("#f9fafb")
TRUST_HIGH = HexColor("#10b981")
TRUST_MEDIUM = HexColor("#f59e0b")
TRUST_LOW = HexColor("#ef4444")
WHITE = white
BLACK = black


async def generate_verification_pdf(
    db: AsyncSession,
    verification_id: int,
) -> Optional[bytes]:
    """
    Generate a branded PDF verification report.
    Returns PDF bytes or None if verification not found or reportlab unavailable.
    """
    if not REPORTLAB_AVAILABLE:
        return None

    from app.services.verification_service import get_verification_by_id

    verification = await get_verification_by_id(db, verification_id)
    if not verification:
        return None

    # Get property details
    prop = None
    if verification.property_id:
        from app.services.property_service import get_property_by_id
        prop = await get_property_by_id(db, verification.property_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=20*mm,
        title=f"Vestra Trust Report — Property #{verification.property_id or 'N/A'}",
        author="Vestra AI",
    )

    styles = getSampleStyleSheet()
    story = _build_report_story(verification, prop, styles, doc)

    try:
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        logger.error('{"event":"pdf_generation_failed","verification_id":%d,"error":"%s"}',
                     verification_id, str(e))
        return None


def _build_report_story(verification, prop, styles, doc) -> list:
    """Build the full report story (list of flowables)."""
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    header_style = ParagraphStyle(
        'VestraHeader', parent=styles['Heading1'],
        fontSize=22, textColor=VESTRA_DARK, alignment=TA_CENTER,
        spaceAfter=4*mm,
    )
    story.append(Paragraph("VESTRA Trust Report", header_style))
    story.append(Paragraph(
        f"<i>AI-Powered Property Verification — Report #{verification.id}</i>",
        ParagraphStyle('Subtitle', parent=styles['Normal'],
                       fontSize=10, textColor=VESTRA_GREY, alignment=TA_CENTER,
                       spaceAfter=10*mm)
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=VESTRA_GREEN, spaceAfter=8*mm))

    # ── Property Summary ────────────────────────────────────────────────────
    story.append(Paragraph("Property Details", styles['Heading2']))

    prop_data = [
        ["Property ID", str(verification.property_id or "N/A")],
        ["Title", prop.title if prop else "N/A"],
        ["Location", f"{prop.city}, {prop.county}" if prop else "N/A"],
        ["Type", f"{prop.property_type} / {prop.listing_type}" if prop else "N/A"],
        ["Price", f"KES {prop.price:,.0f}" if prop and prop.price else "N/A"],
        ["Bedrooms", str(prop.bedrooms or "N/A") if prop else "N/A"],
        ["Size", f"{prop.size_sqft:,.0f} sqft" if prop and prop.size_sqft else "N/A"],
    ]

    prop_table = Table(prop_data, colWidths=[50*mm, 110*mm])
    prop_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), VESTRA_LIGHT_BG),
        ('TEXTCOLOR', (0, 0), (0, -1), VESTRA_DARK),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, VESTRA_GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(prop_table)
    story.append(Spacer(1, 8*mm))

    # ── Trust Score Gauge ───────────────────────────────────────────────────
    trust_score = verification.trust_score or 0
    fraud_score = verification.fraud_risk_score or 0

    story.append(Paragraph("Trust & Fraud Assessment", styles['Heading2']))

    gauge_text = _trust_score_gauge_text(trust_score)
    trust_color = _trust_color(trust_score)

    score_style = ParagraphStyle(
        'TrustScore', parent=styles['Normal'],
        fontSize=36, textColor=trust_color, alignment=TA_CENTER,
        spaceAfter=2*mm,
    )
    story.append(Paragraph(f"<b>{trust_score:.0f}/100</b>", score_style))
    story.append(Paragraph(
        gauge_text,
        ParagraphStyle('TrustLabel', parent=styles['Normal'],
                       fontSize=12, alignment=TA_CENTER, textColor=trust_color,
                       spaceAfter=6*mm)
    ))

    # Scores table
    scores_data = [
        ["Metric", "Score", "Rating"],
        ["Trust Score", f"{trust_score:.0f}/100", _trust_label(trust_score)],
        ["Fraud Risk", f"{fraud_score:.0f}/100", _fraud_label(fraud_score)],
        ["Ownership Confidence", verification.ownership_confidence or "N/A", ""],
        ["Price Reasonableness", verification.price_reasonableness or "N/A", ""],
        ["AI Recommendation", verification.ai_recommendation or "N/A", _rec_emoji(verification.ai_recommendation)],
    ]

    scores_table = Table(scores_data, colWidths=[55*mm, 45*mm, 60*mm])
    scores_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), VESTRA_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, VESTRA_GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [VESTRA_LIGHT_BG, WHITE]),
    ]))
    story.append(scores_table)
    story.append(Spacer(1, 8*mm))

    # ── Document Flags ──────────────────────────────────────────────────────
    if verification.document_flags:
        story.append(Paragraph("Document Issues & Flags", styles['Heading2']))
        for flag in verification.document_flags:
            story.append(Paragraph(
                f"• {flag}",
                ParagraphStyle('Flag', parent=styles['Normal'], fontSize=10,
                               leftIndent=10, spaceAfter=3)
            ))
        story.append(Spacer(1, 6*mm))

    # ── AI Summary ──────────────────────────────────────────────────────────
    if verification.ai_summary:
        story.append(Paragraph("AI Analysis Summary", styles['Heading2']))
        summary_style = ParagraphStyle(
            'Summary', parent=styles['Normal'],
            fontSize=10, leading=14, backColor=VESTRA_LIGHT_BG,
            leftIndent=5, rightIndent=5, spaceBefore=3*mm, spaceAfter=6*mm,
            borderPadding=10,
        )
        story.append(Paragraph(verification.ai_summary, summary_style))

    # ── Footer ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=VESTRA_GREEN, spaceBefore=10*mm))
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=VESTRA_GREY, alignment=TA_CENTER,
    )
    now_str = datetime.now(timezone.utc).strftime("%d %B %Y at %H:%M UTC")
    story.append(Paragraph(
        f"Generated by Vestra AI on {now_str} | Report #{verification.id}<br/>"
        f"Vestra — Africa's Most Trusted Property Platform | vestra.co.ke<br/>"
        f"This report is for informational purposes. Always conduct independent due diligence.",
        footer_style
    ))

    return story


# ── Helper functions ─────────────────────────────────────────────────────────────

def _trust_color(score: float) -> HexColor:
    if score >= 75:
        return TRUST_HIGH
    elif score >= 50:
        return TRUST_MEDIUM
    return TRUST_LOW


def _trust_label(score: float) -> str:
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 50:
        return "Fair"
    elif score >= 30:
        return "Poor"
    return "Very Poor"


def _trust_score_gauge_text(score: float) -> str:
    if score >= 90:
        return "✅ HIGH TRUST — This property shows strong trust signals."
    elif score >= 75:
        return "✅ GOOD TRUST — Generally reliable with minor concerns."
    elif score >= 50:
        return "⚠️ MODERATE TRUST — Exercise caution. Review flagged items."
    elif score >= 30:
        return "⚠️ LOW TRUST — Multiple concerns. Independent verification strongly advised."
    return "🚫 VERY LOW TRUST — High risk. Do not proceed without full due diligence."


def _fraud_label(score: float) -> str:
    if score < 25:
        return "Low Risk"
    elif score < 55:
        return "Medium Risk"
    return "High Risk"


def _rec_emoji(rec: Optional[str]) -> str:
    if not rec:
        return ""
    return {"approve": "✅ Approved", "review": "⚠️ Review", "reject": "🚫 Rejected"}.get(rec, rec)
