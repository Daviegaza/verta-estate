"""
Generate VESTRA Operations & Monitoring Guide PDF.
Run: python generate_operations_guide.py
Output: VESTRA_Operations_Guide.pdf
"""
import os
import sys
from datetime import datetime, timezone
from io import BytesIO

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem, KeepTogether
)

OUTPUT = os.path.join(os.path.dirname(__file__), "VESTRA_Operations_Guide.pdf")

# ── Brand Colors ──
GREEN = HexColor("#10b981")
DARK = HexColor("#064e3b")
GREY = HexColor("#6b7280")
LIGHT_BG = HexColor("#f9fafb")
AMBER = HexColor("#f59e0b")
RED = HexColor("#ef4444")
BLUE = HexColor("#3b82f6")

def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=15*mm, bottomMargin=20*mm,
        title="VESTRA Operations & Monitoring Guide v3.0.0",
        author="Vestra Engineering",
    )
    styles = getSampleStyleSheet()
    story = []

    # ── Helper styles ──
    h1 = ParagraphStyle('h1', parent=styles['Heading1'], fontSize=22, textColor=DARK, spaceAfter=6*mm, spaceBefore=8*mm)
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=16, textColor=DARK, spaceAfter=4*mm, spaceBefore=6*mm)
    h3 = ParagraphStyle('h3', parent=styles['Heading3'], fontSize=13, textColor=DARK, spaceAfter=2*mm, spaceBefore=5*mm)
    body = ParagraphStyle('body', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=3*mm)
    code = ParagraphStyle('code', parent=styles['Normal'], fontSize=8.5, leading=11, fontName='Courier', backColor=LIGHT_BG, borderPadding=8, spaceAfter=4*mm, leftIndent=5, rightIndent=5)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, textColor=GREY, leading=10)
    table_cell = ParagraphStyle('tc', parent=styles['Normal'], fontSize=9, leading=12)
    table_header = ParagraphStyle('th', parent=styles['Normal'], fontSize=9, leading=12, textColor=white, fontName='Helvetica-Bold')

    def header_row(text):
        return Paragraph(f"<b>{text}</b>", table_header)

    def cell(text):
        return Paragraph(str(text), table_cell)

    # ═══════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph("VESTRA", ParagraphStyle('cover', parent=h1, fontSize=42, alignment=TA_CENTER, textColor=GREEN)))
    story.append(Paragraph("Operations & Monitoring Guide", ParagraphStyle('cover2', parent=h2, fontSize=22, alignment=TA_CENTER, textColor=DARK)))
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("Version 3.0.0 — June 2026", ParagraphStyle('cv', parent=body, alignment=TA_CENTER, textColor=GREY)))
    story.append(Paragraph("AI-Powered Property Trust Platform for Africa", ParagraphStyle('cv2', parent=body, alignment=TA_CENTER)))
    story.append(Spacer(1, 20*mm))
    story.append(HRFlowable(width="60%", thickness=2, color=GREEN, spaceAfter=10*mm))

    # Quick links
    links_data = [
        ["Backend API", "http://localhost:8000"],
        ["Swagger Docs", "http://localhost:8000/docs"],
        ["Health Check", "http://localhost:8000/health"],
        ["Prometheus Metrics", "http://localhost:8000/metrics"],
        ["Frontend", "http://localhost:3000"],
        ["Vestra Website", "https://vestra.co.ke"],
    ]
    links_table = Table(links_data, colWidths=[45*mm, 80*mm])
    links_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), DARK),
        ('TEXTCOLOR', (1, 0), (1, -1), BLUE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
    ]))
    story.append(links_table)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Table of Contents", h1))
    toc_items = [
        "1. Quick Start — Running the System",
        "2. Architecture Overview",
        "3. Backend Deep Dive",
        "4. Monitoring & Health Checks",
        "5. Prometheus Metrics Reference",
        "6. Logging & Observability",
        "7. Database Operations",
        "8. Redis Caching Layer",
        "9. Security Architecture",
        "10. API Route Reference (22 modules, 85+ endpoints)",
        "11. Environment Configuration",
        "12. Docker Deployment",
        "13. Troubleshooting",
        "14. Demo Credentials & Seed Data",
    ]
    for item in toc_items:
        story.append(Paragraph(item, body))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 1. QUICK START
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. Quick Start — Running the System", h1))

    story.append(Paragraph("Option A: PowerShell Startup Scripts (Windows)", h2))
    story.append(Paragraph("From the <b>vestra/</b> directory, run:", body))
    story.append(Paragraph("./start-all.ps1", code))
    story.append(Paragraph("This launches both backend (port 8000) and frontend (port 3000) in separate minimized PowerShell windows.", body))

    story.append(Paragraph("Option B: Manual Start", h2))
    story.append(Paragraph("<b>Backend (Terminal 1):</b>", body))
    story.append(Paragraph("cd vestra/backend\nvenv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload", code))
    story.append(Paragraph("<b>Frontend (Terminal 2):</b>", body))
    story.append(Paragraph("cd vestra/frontend-build\nnpm run dev", code))

    story.append(Paragraph("Option C: Docker (Production)", h2))
    story.append(Paragraph("export POSTGRES_PASSWORD=secure_password\nexport REDIS_PASSWORD=secure_redis\nexport SECRET_KEY=$(openssl rand -base64 64)\ndocker-compose up -d", code))

    story.append(Paragraph("Verification", h2))
    story.append(Paragraph("After starting, verify the system is healthy:", body))
    story.append(Paragraph("# Backend health check\ncurl http://localhost:8000/health\n\n# Should return {\"status\":\"healthy\",\"database\":\"connected\",\"redis\":\"connected\"}", code))

    story.append(Paragraph("Stop the System", h2))
    story.append(Paragraph("./stop-all.ps1", code))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 2. ARCHITECTURE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. Architecture Overview", h1))
    story.append(Paragraph(
        "Vestra is an AI-powered property trust platform with a FastAPI backend, Next.js 16 frontend, "
        "PostgreSQL 16 database, and Redis 7 caching layer. The AI engine is entirely rule-based "
        "(no external API calls), providing sub-10ms fraud detection, trust scoring, and property valuation.",
        body
    ))

    arch_data = [
        ["Layer", "Technology", "Port", "Purpose"],
        ["Frontend", "Next.js 16 + React 19.2 + TypeScript", "3000", "PWA with offline support"],
        ["API Gateway", "FastAPI 0.111 + Uvicorn", "8000", "REST API + WebSocket"],
        ["AI Engine", "Built-in rule-based (Python)", "—", "7 sub-engines, zero external APIs"],
        ["Database", "PostgreSQL 16 (asyncpg)", "5432", "6 tables, 30+ indexes, FTS"],
        ["Cache", "Redis 7 (redis-py)", "6379", "6-layer caching, rate limiting"],
        ["Payments", "M-Pesa Daraja + Stripe", "—", "STK Push, B2C, webhooks"],
        ["Messaging", "WhatsApp Business API", "—", "Chat + notifications"],
        ["Monitoring", "Prometheus + Structured Logging", "8000", "/metrics endpoint"],
    ]
    arch_table = Table(arch_data, colWidths=[30*mm, 55*mm, 18*mm, 65*mm])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 8*mm))

    story.append(Paragraph("Request Flow (Example: AI Property Search)", h2))
    story.append(Paragraph(
        "1. User submits search → Next.js calls GET /api/properties/ai-search?q=...<br/>"
        "2. SecurityHeadersMiddleware adds CSP/HSTS/X-Frame headers<br/>"
        "3. RateLimitMiddleware checks Redis sliding window (120 req/min)<br/>"
        "4. GzipCompressionMiddleware compresses response >1KB<br/>"
        "5. RequestLoggingMiddleware assigns correlation ID + logs timing<br/>"
        "6. Route handler calls VestraAI search parser → structured filters<br/>"
        "7. search_properties() → Redis cache check (2-min TTL) → PostgreSQL FTS<br/>"
        "8. GIN index scan → relevance-ranked results → JSON response<br/>"
        "9. Response headers: X-Correlation-ID, X-Response-Time-Ms, X-RateLimit-Remaining",
        body
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 3. BACKEND DEEP DIVE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. Backend Deep Dive", h1))

    story.append(Paragraph("Middleware Stack (applied in order)", h2))
    mw_data = [
        ["#", "Middleware", "Purpose"],
        ["1", "SecurityHeadersMiddleware", "CSP, HSTS, X-Frame-Options, X-XSS-Protection, Permissions-Policy"],
        ["2", "RequestSizeLimitMiddleware", "Rejects requests >5MB with 413"],
        ["3", "RateLimitMiddleware", "Redis sliding-window: Auth 10/min, General 120/min, Admin 300/min"],
        ["4", "GzipCompressionMiddleware", "Compresses text/json >1KB (gzip level 6)"],
        ["5", "metrics_middleware", "Prometheus: REQUEST_COUNT, REQUEST_LATENCY, REQUEST_IN_FLIGHT"],
        ["6", "RequestLoggingMiddleware", "JSON logs: correlation_id, method, path, status, duration_ms, IP"],
        ["7", "CORSMiddleware", "Allow origins from settings, expose rate-limit/correlation headers"],
    ]
    mw_table = Table(mw_data, colWidths=[8*mm, 50*mm, 110*mm])
    mw_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(mw_table)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("AI Engine — 7 Sub-Engines", h2))
    ai_data = [
        ["Engine", "Function", "Latency"],
        ["FraudDetector", "Keyword scan (23 keywords), price sanity, document check, agent verification", "<10ms"],
        ["TrustEngine", "Composite 0-100 with ownership confidence + recommendation", "<5ms"],
        ["PriceAnalyser", "City price band comparison, bedroom adjustment, 20% tolerance", "<5ms"],
        ["SearchParser", "Natural language → structured filters (city, bedrooms, price, type)", "<10ms"],
        ["DocumentAnalyser", "Checks submitted docs against required list per listing type", "<5ms"],
        ["ValuationEngine", "Size × sqft price, age depreciation, amenity bonus, investment score", "<10ms"],
        ["MarketIntelligence", "City-level trends, supply/demand, best time to buy, investor tips", "<5ms"],
    ]
    ai_table = Table(ai_data, colWidths=[32*mm, 106*mm, 20*mm])
    ai_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(ai_table)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 4. MONITORING & HEALTH CHECKS
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. Monitoring & Health Checks", h1))

    story.append(Paragraph("Health Endpoints", h2))
    health_data = [
        ["Endpoint", "Method", "Purpose", "Response Example"],
        ["/health", "GET", "Full health (DB + Redis check)", '{"status":"healthy","database":"connected","redis":"connected"}'],
        ["/health/live", "GET", "K8s liveness probe (minimal)", '{"status":"alive"}'],
        ["/health/ready", "GET", "K8s readiness probe (DB check)", '{"status":"ready"}'],
        ["/metrics", "GET", "Prometheus metrics endpoint", "vestra_http_requests_total{...} 1234"],
        ["/", "GET", "Root info (version, env)", '{"name":"Vestra","version":"3.0.0","status":"operational"}'],
        ["/api/monitoring/health/full", "GET", "Detailed health (auth required)", "Full system health + services"],
        ["/api/monitoring/health/services", "GET", "Service status breakdown", "DB, Redis, M-Pesa, Stripe, WhatsApp"],
        ["/api/monitoring/health/resources", "GET", "CPU, memory, disk usage", "System resource metrics"],
        ["/api/monitoring/health/database", "GET", "DB pool stats, query times", "Connection pool metrics"],
        ["/api/monitoring/health/redis", "GET", "Redis memory, keys, hits", "Cache hit rate, memory usage"],
    ]
    health_table = Table(health_data, colWidths=[40*mm, 14*mm, 35*mm, 75*mm])
    health_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(health_table)
    story.append(Spacer(1, 8*mm))

    story.append(Paragraph("Health Check Responses Reference", h2))
    story.append(Paragraph("<b>Healthy:</b> status = 'healthy', database = 'connected', redis = 'connected'", body))
    story.append(Paragraph("<b>Degraded:</b> status = 'degraded', one dependency shows 'error: ...' or 'unavailable'", body))
    story.append(Paragraph("<b>Down:</b> /health/live returns non-200 or times out", body))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("Response Headers (Every API Response)", h2))
    headers_data = [
        ["Header", "Value", "Purpose"],
        ["X-Content-Type-Options", "nosniff", "Prevent MIME sniffing"],
        ["X-Frame-Options", "DENY", "Prevent clickjacking"],
        ["X-XSS-Protection", "1; mode=block", "XSS filter"],
        ["Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload", "Enforce HTTPS (1 year)"],
        ["Referrer-Policy", "strict-origin-when-cross-origin", "Privacy"],
        ["Permissions-Policy", "camera=(), microphone=(), geolocation=(self), payment=(self)", "Browser feature access"],
        ["X-Correlation-ID", "<uuid>", "Request tracing across services"],
        ["X-Response-Time-Ms", "<ms>", "Server processing time"],
        ["X-RateLimit-Remaining", "<count>", "Requests remaining in window"],
    ]
    headers_table = Table(headers_data, colWidths=[42*mm, 60*mm, 62*mm])
    headers_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(headers_table)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 5. PROMETHEUS METRICS
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("5. Prometheus Metrics Reference", h1))
    story.append(Paragraph("All metrics exposed at <b>GET /metrics</b> in Prometheus text format.", body))

    metrics_data = [
        ["Metric Name", "Type", "Labels", "Description"],
        ["vestra_http_requests_total", "Counter", "method, endpoint, status", "Total HTTP requests"],
        ["vestra_http_request_duration_seconds", "Histogram", "method, endpoint", "Request latency distribution"],
        ["vestra_http_requests_in_flight", "Gauge", "—", "Concurrent requests being processed"],
        ["vestra_properties_listed_total", "Counter", "property_type, listing_type", "Properties created"],
        ["vestra_verifications_run_total", "Counter", "recommendation", "AI verifications executed"],
        ["vestra_payments_received_total", "Counter", "method, purpose", "Payment count"],
        ["vestra_payments_amount_kes_total", "Counter", "purpose", "Revenue in KES"],
        ["vestra_users_registered_total", "Counter", "role", "Signup count by role"],
        ["vestra_fraud_risk_score", "Histogram", "—", "Fraud score distribution (0-100)"],
        ["vestra_trust_score", "Histogram", "—", "Trust score distribution (0-100)"],
    ]
    metrics_table = Table(metrics_data, colWidths=[48*mm, 18*mm, 30*mm, 64*mm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Example Prometheus Configuration", h2))
    story.append(Paragraph("scrape_configs:\n  - job_name: 'vestra'\n    scrape_interval: 15s\n    static_configs:\n      - targets: ['localhost:8000']\n    metrics_path: '/metrics'", code))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 6. LOGGING
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("6. Logging & Observability", h1))
    story.append(Paragraph("All logs are structured JSON. Every request gets a unique correlation_id for tracing.", body))
    story.append(Paragraph("<b>Log Format:</b>", body))
    story.append(Paragraph(r'{"event":"user_registered","user_id":42,"correlation_id":"abc123"}', code))
    story.append(Paragraph("<b>Key Events Logged:</b>", body))
    story.append(Paragraph(
        "• <b>startup</b> — App name, version, environment, Redis connection status<br/>"
        "• <b>shutdown</b> — Graceful shutdown with resource cleanup<br/>"
        "• <b>request</b> — Every HTTP request with method, path, status, duration_ms, client_ip<br/>"
        "• <b>unhandled_error</b> — Full traceback for unexpected exceptions<br/>"
        "• <b>user_registered / user_login</b> — Auth events<br/>"
        "• <b>property_created / property_verified</b> — Property lifecycle<br/>"
        "• <b>payment_initiated / payment_completed</b> — Payment flow<br/>"
        "• <b>subscription_created / subscription_cancelled</b> — Subscription events<br/>"
        "• <b>fraud_reported / fraud_reviewed</b> — Trust & safety<br/>"
        "• <b>escrow_created / escrow_released</b> — Escrow lifecycle<br/>"
        "• <b>dispute_created / dispute_resolved</b> — Dispute workflow<br/>",
        body
    ))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("<b>Slow Request Detection:</b> Requests >1 second are logged at WARNING level.", body))
    story.append(Paragraph("<b>Log Level:</b> INFO in development, WARNING in production (configurable via LOG_LEVEL env var).", body))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 7. DATABASE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("7. Database Operations", h1))

    story.append(Paragraph("Connection Pool Configuration", h2))
    db_data = [
        ["Setting", "Value", "Description"],
        ["DATABASE_POOL_SIZE", "20", "Base pool size"],
        ["DATABASE_MAX_OVERFLOW", "40", "Extra connections above base"],
        ["DATABASE_POOL_RECYCLE", "3600s", "Recycle connections after 1 hour"],
        ["pool_pre_ping", "True", "Verify connections before use"],
        ["pool_timeout", "30s", "Wait up to 30s for a connection"],
        ["expire_on_commit", "False", "Prevents MissingGreenlet errors in async"],
    ]
    db_table = Table(db_data, colWidths=[45*mm, 25*mm, 95*mm])
    db_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(db_table)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Tables (7 core tables)", h2))
    tables_data = [
        ["Table", "Rows (seed)", "Key Indexes"],
        ["users", "9", "email UNIQUE, phone UNIQUE, role"],
        ["properties", "16", "16 indexes incl. GIN FTS, city, county, price, status"],
        ["agent_profiles", "2", "user_id UNIQUE, badge_level"],
        ["documents", "20+", "property_id, uploader_id, document_type"],
        ["verifications", "17", "property_id, status, trust_score"],
        ["payments", "21", "user_id, status, checkout_request_id, reference UNIQUE"],
        ["audit_logs", "—", "user_id, action, resource_type, created_at"],
    ]
    tables_table = Table(tables_data, colWidths=[32*mm, 20*mm, 110*mm])
    tables_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(tables_table)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 8. REDIS CACHING
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("8. Redis Caching Layer", h1))
    story.append(Paragraph("Vestra uses 6 layers of caching for sub-10ms response times:", body))

    cache_data = [
        ["Layer", "TTL", "What's Cached"],
        ["Browser (Service Worker)", "Indefinite", "Static assets (JS, CSS, images, fonts) — PWA offline"],
        ["HTTP Cache Headers", "Per-response", "Cache-Control: no-store for API, ETags for static"],
        ["Redis — Property Detail", "300s (5 min)", "Single property JSON, cache-aside pattern"],
        ["Redis — Property Listings", "120s (2 min)", "Search results hashed by params"],
        ["Redis — AI Valuation", "600s (10 min)", "Valuation results hashed by property attributes"],
        ["Redis — Market Insights", "1800s (30 min)", "City-level data changes slowly"],
        ["Redis — Admin Stats", "120s (2 min)", "Dashboard stats (15+ expensive queries cached)"],
        ["DB Connection Pool", "—", "20+40 connections, pre-ping, recycle 3600s"],
        ["PostgreSQL Shared Buffers", "—", "Frequently accessed data in RAM, index-only scans"],
    ]
    cache_table = Table(cache_data, colWidths=[48*mm, 30*mm, 85*mm])
    cache_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(cache_table)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Cache Key Schema", h2))
    story.append(Paragraph(
        "vestra:cache:&lt;prefix&gt;:&lt;sha256hash[:16]&gt; — Cached function results<br/>"
        "vestra:ratelimit:&lt;type&gt;:&lt;client_ip&gt; — Rate limit windows<br/>"
        "vestra:refresh:&lt;user_id&gt;:&lt;token_jti&gt; — Refresh tokens<br/>"
        "vestra:email_verify:&lt;token&gt; — Email verification (24h TTL)<br/>"
        "vestra:pw_reset:&lt;token&gt; — Password reset (30min TTL)<br/>"
        "vestra:search:&lt;sha256hash[:16]&gt; — Search results (2min TTL)<br/>"
        "vestra:sub:&lt;user_id&gt; — User subscription (5min TTL)",
        body
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 9. SECURITY
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("9. Security Architecture", h1))

    sec_data = [
        ["Threat", "Protection"],
        ["Brute Force", "Redis rate limiting: 10 auth req/min per IP, 5-fail account lockout (15 min)"],
        ["XSS", "Content-Security-Policy headers, output encoding"],
        ["Clickjacking", "X-Frame-Options: DENY"],
        ["MIME Sniffing", "X-Content-Type-Options: nosniff"],
        ["MITM", "HSTS max-age=31536000; includeSubDomains; preload"],
        ["CSRF", "CSRF protection enabled in settings"],
        ["SQL Injection", "SQLAlchemy ORM parameterized queries exclusively"],
        ["File Upload", "Type validation + 10MB size limit + MIME type whitelist"],
        ["User Enumeration", "Forgot password returns same response regardless of email existence"],
        ["DDoS", "Rate limiting per endpoint type, 5MB request body size limit"],
        ["API Key Theft", "SHA-256 hashed storage, shown only once on creation"],
        ["M-Pesa Callback", "Safaricom IP whitelist + HMAC signature verification + replay protection"],
        ["WhatsApp Webhook", "HMAC-SHA256 signature verification on all messages"],
    ]
    sec_table = Table(sec_data, colWidths=[38*mm, 125*mm])
    sec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(sec_table)
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("Auth: JWT (HS256) + bcrypt, 60-min access tokens, 7-day refresh tokens, 6 RBAC roles.", body))
    story.append(Paragraph("Production Requirements: SECRET_KEY ≥32 chars, REDIS_PASSWORD set, DATABASE_URL has ?ssl=require, TURNSTILE_SECRET_KEY set for CAPTCHA, DEBUG=False.", body))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 10. API ROUTE REFERENCE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("10. API Route Reference (22 Modules, 85+ Endpoints)", h1))

    routes_summary = [
        ["Module", "Prefix", "Endpoints", "Auth"],
        ["Auth (email)", "/api/auth", "8 (register, login, me, change-password, forgot/reset-password, verify-email)", "Mixed"],
        ["OTP Auth", "/api/auth/otp", "3 (send-otp, verify-otp, login)", "Mixed"],
        ["Properties", "/api/properties", "9 (CRUD, AI search, FTS, my, publish, listing-fee, feature)", "Mixed"],
        ["Verification", "/api/verify", "6 (request, run AI, status, documents upload, admin review)", "Mixed"],
        ["Payments", "/api/payments", "4 (mpesa initiate, mpesa callback, status, my)", "Mixed"],
        ["Admin", "/api/admin", "12 (stats, users CRUD, properties, verifications, payments, audit, fraud, KYC)", "Admin"],
        ["AI Routes", "/api/ai", "4 (valuate, market insights, search parse)", "Bearer"],
        ["WhatsApp", "/api/whatsapp", "7 (webhook, send text/card/report/payment, broadcast)", "Mixed"],
        ["Subscriptions", "/api/subscriptions", "4 (plans, my, subscribe, cancel)", "Bearer"],
        ["Rentals", "/api/rentals", "7 (collect, schedule, units, dashboard, payments, receipt)", "Bearer"],
        ["KYC", "/api/kyc", "4 (submit, status, admin pending, admin review)", "Bearer"],
        ["Notifications", "/api/notifications", "5 (list, unread-count, mark-read, mark-all-read, preferences)", "Bearer"],
        ["Messages", "/api/messages", "5 (send, conversations, conversation, mark-read, unread-count)", "Bearer"],
        ["Fraud", "/api/fraud", "4 (report, check-blacklist, admin pending, admin review)", "Bearer"],
        ["Favorites", "/api/favorites", "4 (add, remove, list, check)", "Bearer"],
        ["Reports", "/api/reports", "2 (verification report JSON + PDF download)", "Bearer"],
        ["Enterprise", "/api/enterprise", "6 (keys CRUD, usage, webhooks CRUD)", "Bearer"],
        ["Monitoring", "/api/monitoring", "5 (health full/services/resources/database/redis)", "Bearer"],
        ["Escrow", "/api/escrow", "9 (CRUD, deposit, balance, release, cancel, dispute, admin)", "Bearer"],
        ["Disputes", "/api/disputes", "8 (file, categories, my, detail, admin assign/resolve/stats)", "Bearer"],
        ["Reviews", "/api/reviews", "5 (write, subject, my, property stats, top agents)", "Mixed"],
        ["Payouts", "/api/payouts", "7 (request, my, detail, admin process/complete/fail/stats)", "Bearer"],
        ["Coupons", "/api/coupons", "3 (validate, apply, admin list)", "Bearer"],
    ]
    # Split into two pages
    half = len(routes_summary) // 2 + 1
    for i, chunk in enumerate([routes_summary[:half], routes_summary[half:]]):
        rt = Table(chunk, colWidths=[28*mm, 26*mm, 55*mm, 14*mm])
        rt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
        ]))
        story.append(rt)
        story.append(Spacer(1, 4*mm))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 11. ENV CONFIG
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("11. Environment Configuration", h1))
    story.append(Paragraph("All settings are in <b>vestra/backend/.env</b> with type-safe defaults in <b>app/core/config.py</b>.", body))

    env_data = [
        ["Category", "Variable", "Default", "Required in Prod?"],
        ["Database", "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/vestra", "YES (with ?ssl=require)"],
        ["Database", "DATABASE_POOL_SIZE", "20", "No"],
        ["Database", "DATABASE_MAX_OVERFLOW", "40", "No"],
        ["Redis", "REDIS_URL", "redis://localhost:6379/0", "YES"],
        ["Redis", "REDIS_PASSWORD", '""', "YES (production)"],
        ["Auth", "SECRET_KEY", "change-me-...", "YES (≥32 chars)"],
        ["Auth", "ACCESS_TOKEN_EXPIRE_MINUTES", "60", "No"],
        ["M-Pesa", "MPESA_CONSUMER_KEY", '""', "For M-Pesa"],
        ["M-Pesa", "MPESA_CONSUMER_SECRET", '""', "For M-Pesa"],
        ["M-Pesa", "MPESA_SHORTCODE", "174379", "For M-Pesa"],
        ["M-Pesa", "MPESA_PASSKEY", '""', "For M-Pesa"],
        ["M-Pesa", "MPESA_ENV", "sandbox", "Change to production"],
        ["Stripe", "STRIPE_SECRET_KEY", '""', "For Stripe"],
        ["Email", "SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD", '""', "For email"],
        ["WhatsApp", "WHATSAPP_PHONE_NUMBER_ID / ACCESS_TOKEN", '""', "For WhatsApp"],
        ["CAPTCHA", "TURNSTILE_SECRET_KEY / SITE_KEY", '""', "YES (production)"],
        ["App", "APP_NAME", "Vestra", "No"],
        ["App", "APP_VERSION", "3.0.0", "No"],
        ["App", "ENVIRONMENT", "development", "Set to production"],
        ["App", "CORS_ORIGINS", "http://localhost:3000", "Set to frontend URL"],
        ["App", "BASE_URL", "http://localhost:3000", "Set to public URL"],
        ["Rate Limit", "RATE_LIMIT_AUTH_PER_MINUTE", "10", "No"],
        ["Rate Limit", "RATE_LIMIT_GENERAL_PER_MINUTE", "120", "No"],
        ["Rate Limit", "RATE_LIMIT_ADMIN_PER_MINUTE", "300", "No"],
        ["Lockout", "ACCOUNT_LOCKOUT_MAX_ATTEMPTS", "5", "No"],
        ["Lockout", "ACCOUNT_LOCKOUT_DURATION_MINUTES", "15", "No"],
    ]
    env_table = Table(env_data, colWidths=[25*mm, 55*mm, 50*mm, 33*mm])
    env_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(env_table)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 12. DOCKER
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("12. Docker Deployment", h1))
    story.append(Paragraph("Full stack via <b>docker-compose.yml</b> — 4 services:", body))

    docker_data = [
        ["Service", "Image", "Resources", "Port"],
        ["postgres", "postgres:16-alpine", "512MB limit, data checksums", "5432"],
        ["redis", "redis:7-alpine", "256MB maxmemory, allkeys-lru, AOF", "6379"],
        ["backend", "Custom (multi-stage)", "1GB limit, 4 Gunicorn workers", "8000"],
        ["frontend", "Custom (Next.js standalone)", "—", "3000"],
    ]
    docker_table = Table(docker_data, colWidths=[28*mm, 48*mm, 58*mm, 22*mm])
    docker_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(docker_table)
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("Deployment Platforms Supported:", body))
    story.append(Paragraph("• Fly.io (Nairobi region, 2 CPUs, 1GB)<br/>• Render (blueprint: API + Frontend + PostgreSQL + Redis)<br/>• Railway (2 replicas, Dockerfile)<br/>• Self-hosted VPS (docker-compose)<br/>• Vercel (frontend only, API proxy to backend)", body))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("Gunicorn Production Config:", body))
    story.append(Paragraph(
        "workers = CPU × 2 + 1<br/>"
        "worker_class = uvicorn.workers.UvicornWorker<br/>"
        "max_requests = 10000 (with 1000 jitter)<br/>"
        "timeout = 30s, graceful_timeout = 10s, keepalive = 5s<br/>"
        "backlog = 2048, JSON access logs",
        body
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 13. TROUBLESHOOTING
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("13. Troubleshooting", h1))

    issues = [
        ("Backend won't start", [
            "Check PostgreSQL is running: <font face='Courier'>pg_isready</font>",
            "Check Redis is running: <font face='Courier'>redis-cli ping</font>",
            "Verify .env has correct DATABASE_URL and REDIS_URL",
            "Check port 8000 is free: <font face='Courier'>netstat -ano | findstr 8000</font>",
            "Run seed data: <font face='Courier'>python seed.py</font>",
        ]),
        ("Frontend won't start", [
            "Run <font face='Courier'>npm install</font> from frontend-build/",
            "Check .env.local has NEXT_PUBLIC_API_URL=http://localhost:8000",
            "Clear Next.js cache: <font face='Courier'>rm -rf .next</font>",
            "Check port 3000 is free",
        ]),
        ("Redis connection errors", [
            "Redis is optional — app works without it (caching/rate-limiting disabled)",
            "Start Redis: <font face='Courier'>redis-server</font> or Docker: <font face='Courier'>docker run -p 6379:6379 redis:7-alpine</font>",
        ]),
        ("Rate limited (429 errors)", [
            "Auth: 10 req/min, General: 120 req/min, Admin: 300 req/min",
            "Wait for the window to reset or increase limits in .env",
        ]),
        ("M-Pesa payments failing", [
            "Check MPESA_ENV=sandbox for testing",
            "Sandbox credentials: use Safaricom Daraja test credentials",
            "Verify callback URL is publicly accessible",
        ]),
        ("Slow API responses", [
            "Check /health — if Redis is down, all requests go to DB",
            "Check /api/monitoring/health/database for pool exhaustion",
            "Increase DATABASE_POOL_SIZE or MAX_OVERFLOW if needed",
            "Enable GIN index: run <font face='Courier'>ensure_fts_index()</font> from search_service",
        ]),
    ]
    for title, items in issues:
        story.append(Paragraph(f"<b>{title}</b>", h3))
        for item in items:
            story.append(Paragraph(f"• {item}", body))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # 14. DEMO CREDENTIALS
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("14. Demo Credentials & Seed Data", h1))
    story.append(Paragraph("All demo users share password: <b>demo1234</b>", body))

    creds_data = [
        ["Name", "Email", "Role", "Notes"],
        ["Admin", "admin@vestra.co.ke", "super_admin", "Full system access"],
        ["Jane Muthoni", "jane.muthoni@email.com", "agent", "Verified agent, gold badge"],
        ["David Kamau", "david.kamau@email.com", "agent", "Verified agent"],
        ["Peter Omondi", "peter.omondi@email.com", "seller", "3 properties listed"],
        ["Faith Wanjiku", "faith.wanjiku@email.com", "seller", "2 properties listed"],
        ["Grace Akinyi", "grace.akinyi@email.com", "landlord", "2 rental units"],
        ["Samuel Njoroge", "samuel.njoroge@email.com", "buyer", "Demo buyer account"],
        ["Mary Wekesa", "mary.wekesa@email.com", "buyer", "Demo buyer account"],
    ]
    creds_table = Table(creds_data, colWidths=[32*mm, 52*mm, 28*mm, 50*mm])
    creds_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_BG, white]),
    ]))
    story.append(creds_table)
    story.append(Spacer(1, 8*mm))

    story.append(Paragraph("Seed Data (16 properties, 17 verifications, 21 payments, 20+ documents)", h2))
    story.append(Paragraph("Load seed data: <font face='Courier'>cd vestra/backend && python seed.py</font>", body))
    story.append(Spacer(1, 10*mm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1.5, color=GREEN, spaceBefore=10*mm))
    story.append(Paragraph(
        f"VESTRA Operations & Monitoring Guide v3.0.0 | Generated {datetime.now(timezone.utc).strftime('%d %B %Y at %H:%M UTC')}<br/>"
        "Vestra — Africa's Most Trusted Property Platform | vestra.co.ke | support@vestra.co.ke<br/>"
        "Built in Nairobi, Kenya. Serving millions across Africa.",
        small
    ))

    # Build
    doc.build(story)
    return OUTPUT


if __name__ == "__main__":
    path = build_pdf()
    print(f"Operations Guide generated: {path}")
    print(f"   Size: {os.path.getsize(path) / 1024:.1f} KB")
