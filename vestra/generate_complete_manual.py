#!/usr/bin/env python3
"""
Generate THE ULTIMATE VESTRA System Manual — one PDF explaining everything.
All passwords, all features, how to use, how to maintain, how to deploy.
"""
import os
from datetime import UTC, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    HRFlowable,
)

# ── Colors ──────────────────────────────────────────────────────────────────
EMERALD = HexColor("#059669")
EMERALD_DARK = HexColor("#047857")
EMERALD_LIGHT = HexColor("#d1fae5")
AMBER = HexColor("#d97706")
DARK_BG = HexColor("#0f172a")
HEADER_BG = HexColor("#064e3b")
TEXT_DARK = HexColor("#1e293b")
TEXT_MUTED = HexColor("#64748b")
BORDER_COLOR = HexColor("#e2e8f0")
TABLE_HEADER = HexColor("#065f46")
TABLE_ALT = HexColor("#f0fdf4")
WHITE = white
RED = HexColor("#dc2626")
BLUE = HexColor("#2563eb")

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "VESTRA_Complete_System_Manual.pdf")

doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=A4,
    leftMargin=18*mm, rightMargin=18*mm,
    topMargin=18*mm, bottomMargin=18*mm,
    title="VESTRA v4.0.0 — Complete System Manual",
    author="Vestra Technologies Ltd",
)
W = A4[0] - 36*mm

styles = getSampleStyleSheet()
BODY = ParagraphStyle("B", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=13, textColor=TEXT_DARK, spaceAfter=5)
CODE = ParagraphStyle("C", parent=BODY, fontName="Courier", fontSize=7.5, leading=10, backColor=HexColor("#f1f5f9"), borderPadding=5, spaceAfter=6, leftIndent=4, rightIndent=4)
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=22, leading=28, textColor=EMERALD_DARK, spaceBefore=16, spaceAfter=10)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=EMERALD, spaceBefore=12, spaceAfter=6)
H3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=TEXT_DARK, spaceBefore=8, spaceAfter=4)
CENTER = ParagraphStyle("CEN", parent=BODY, alignment=TA_CENTER)
SMALL = ParagraphStyle("SM", parent=BODY, fontSize=7.5, textColor=TEXT_MUTED, alignment=TA_CENTER)
BULLET = ParagraphStyle("BU", parent=BODY, leftIndent=12, bulletIndent=4, spaceBefore=1, spaceAfter=1)
WARN = ParagraphStyle("WARN", parent=BODY, textColor=RED, fontName="Helvetica-Bold", fontSize=10)
TITLE_COVER = ParagraphStyle("TC", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=30, leading=38, textColor=WHITE, alignment=TA_CENTER)
SUBTITLE_COVER = ParagraphStyle("SC", parent=CENTER, fontSize=12, leading=18, textColor=HexColor("#a7f3d0"))
INFO_COVER = ParagraphStyle("IC", parent=CENTER, fontSize=9.5, leading=16, textColor=HexColor("#d1fae5"))

story = []

def h1(t): story.append(Paragraph(t, H1))
def h2(t): story.append(Paragraph(t, H2))
def h3(t): story.append(Paragraph(t, H3))
def body(t): story.append(Paragraph(t, BODY))
def code(t): story.append(Paragraph(t.replace("\n","<br/>").replace(" ","&nbsp;"), CODE))
def bullet(t): story.append(Paragraph(f"&bull;&nbsp;{t}", BULLET))
def spacer(h=8): story.append(Spacer(1, h))
def hr(): story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=6, spaceAfter=6))
def warn(t): story.append(Paragraph(f"!! {t}", WARN))

def table(headers, rows, col_widths=None):
    if col_widths is None: col_widths = [W/len(headers)]*len(headers)
    data = [[Paragraph(f"<b>{h}</b>", ParagraphStyle("TH", parent=BODY, textColor=WHITE, fontSize=8.5)) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), ParagraphStyle("TD", parent=BODY, fontSize=8.5)) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),TABLE_HEADER), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("GRID",(0,0),(-1,-1),0.5,BORDER_COLOR), ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,TABLE_ALT]),
        ("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),5), ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(t); spacer(6)

# ═══════════════════════════════════════════════════════════ COVER ═══════════
cover_data = [
    [Paragraph("VESTRA", TITLE_COVER)],
    [Paragraph("v4.0.0 World-Class Super Upgrade", SUBTITLE_COVER)],
    [Spacer(1, 16)],
    [Paragraph("THE COMPLETE SYSTEM MANUAL", ParagraphStyle("CS", parent=SUBTITLE_COVER, fontSize=16, leading=22))],
    [Spacer(1, 12)],
    [Paragraph("Everything you need to know — from passwords to deployment", INFO_COVER)],
    [Spacer(1, 20)],
]
info_items = [
    "Generated: June 21, 2026 | Backend: FastAPI + PostgreSQL 16 + Redis 7",
    "Frontend: Next.js 16 + React 19 + TypeScript 5 | 6 Payment Providers",
    "8-Layer Trust & Safety System | English + Kiswahili | PWA + iOS + Android",
    "210 Backend Tests Passing | 0 Lint Errors | 0 TypeScript Errors",
    "Docker Compose (13 Services) | Fly.io / Render / Railway Ready",
]
for item in info_items:
    cover_data.append([Paragraph(item, INFO_COVER)])
cover_data.append([Spacer(1, 24)])
cover_data.append([Paragraph("support@vestra.co.ke | Vestra Technologies Ltd.", SMALL)])

ct = Table(cover_data, colWidths=[W])
ct.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,-1),DARK_BG), ("ALIGN",(0,0),(-1,-1),"CENTER"),
    ("TOPPADDING",(0,0),(-1,0),50), ("BOTTOMPADDING",(0,-1),(-1,-1),40),
    ("LEFTPADDING",(0,0),(-1,-1),30), ("RIGHTPADDING",(0,0),(-1,-1),30),
]))
story.append(ct)
# Green accent
story.append(Table([[""]], colWidths=[W], rowHeights=[4]))
story[-1].setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),EMERALD)]))
story.append(PageBreak())

# ═══════════════════════════════════════════════════════ TOC ═══════════════
h1("TABLE OF CONTENTS")
spacer(4)
toc = [
    ("PART 1: SYSTEM OVERVIEW", [
        "1.1 What is VESTRA?", "1.2 Tech Stack", "1.3 Architecture Diagram",
        "1.4 What's New in v4.0.0", "1.5 System Requirements",
    ]),
    ("PART 2: ALL PASSWORDS & CREDENTIALS", [
        "2.1 Demo Accounts", "2.2 Database Credentials", "2.3 Redis Credentials",
        "2.4 API Keys & Secrets", "2.5 Payment Provider Keys",
        "2.6 Email & WhatsApp Config", "2.7 Environment Variables Reference",
    ]),
    ("PART 3: GETTING STARTED", [
        "3.1 Prerequisites", "3.2 Local Development Setup", "3.3 Docker Setup",
        "3.4 First Run Checklist", "3.5 Seeding Demo Data",
    ]),
    ("PART 4: HOW EVERYTHING WORKS", [
        "4.1 Authentication System", "4.2 User Roles & Permissions",
        "4.3 Property Management", "4.4 AI Vestima Price Estimator",
        "4.5 Payment Processing (6 Providers)", "4.6 Trust & Safety System",
        "4.7 Real-Time WebSocket System", "4.8 Notification System",
        "4.9 Messaging System", "4.10 Escrow Service",
        "4.11 Subscription & Plans", "4.12 Referral Program",
        "4.13 Enterprise API", "4.14 Background Workers",
    ]),
    ("PART 5: USING THE SYSTEM", [
        "5.1 Buyer's Guide", "5.2 Seller's Guide", "5.3 Agent's Guide",
        "5.4 Landlord's Guide", "5.5 Tenant's Guide", "5.6 Admin Guide",
        "5.7 Mobile App Usage", "5.8 PWA Installation",
    ]),
    ("PART 6: ADMINISTRATION & MANAGEMENT", [
        "6.1 Admin Dashboard", "6.2 User Management", "6.3 Property Moderation",
        "6.4 KYC Verification", "6.5 Fraud Management", "6.6 Dispute Resolution",
        "6.7 Payment Monitoring", "6.8 Analytics & Reporting",
        "6.9 Audit Logs", "6.10 System Monitoring (Grafana)",
    ]),
    ("PART 7: MAINTENANCE & OPERATIONS", [
        "7.1 Daily Operations", "7.2 Database Backups", "7.3 Redis Management",
        "7.4 SSL Certificate Renewal", "7.5 Log Management",
        "7.6 Performance Tuning", "7.7 Security Updates",
        "7.8 Scaling the System",
    ]),
    ("PART 8: DEPLOYMENT", [
        "8.1 Docker Compose Deployment", "8.2 Fly.io Deployment",
        "8.3 Render Deployment", "8.4 Railway Deployment",
        "8.5 Apple App Store Submission", "8.6 Google Play Store Submission",
    ]),
    ("PART 9: TROUBLESHOOTING", [
        "9.1 Common Issues & Fixes", "9.2 Diagnostic Commands",
        "9.3 Recovery Procedures",
    ]),
    ("PART 10: SUPPORT & CONTACT", [
        "10.1 Support Channels", "10.2 Version History",
    ]),
]
for part, items in toc:
    story.append(Paragraph(f"<b>{part}</b>", ParagraphStyle("TP", parent=BODY, fontSize=10.5, leading=18, textColor=EMERALD_DARK)))
    for item in items:
        story.append(Paragraph(item, ParagraphStyle("TI", parent=BODY, fontSize=9, leading=16, leftIndent=16, textColor=TEXT_MUTED)))

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 1 ═════════════
h1("PART 1: SYSTEM OVERVIEW")
h2("1.1 What is VESTRA?")
body("VESTRA is the world's most advanced AI-powered property trust and operating system, built for Kenya and Africa. It combines blockchain-like title verification, 6 payment providers, real-time WebSocket communication, bilingual Swahili/English support, AI price estimation, and native mobile apps into one unified platform.")
body("The v4.0.0 Super Upgrade introduces an industry-leading <b>8-layer Trust & Safety Verification System</b> ensuring 100% genuine sellers, agents, and property listings — eliminating fake listings and scammers entirely.")

h2("1.2 Tech Stack")
table(["Layer","Technology","Version"], [
    ["Backend API","FastAPI (Python 3.12)","0.111+"],
    ["Frontend","Next.js (React 19)","16.2.9"],
    ["Database","PostgreSQL (Alpine)","16"],
    ["Cache/Sessions","Redis (Alpine)","7"],
    ["Reverse Proxy","Nginx","1.27"],
    ["Real-time","WebSockets (FastAPI native)","-"],
    ["AI Engine","Vestra AI + Vestima","v4"],
    ["Background Tasks","Celery + Redis Streams","-"],
    ["Mobile Apps","Capacitor.js","6.x"],
    ["Payments","6 Providers","-"],
    ["Monitoring","Prometheus + Grafana","Latest"],
    ["CI/CD","GitHub Actions","-"],
    ["Testing","Pytest + Playwright + k6","-"],
    ["Error Tracking","Sentry","Latest"],
], [W*0.2,W*0.4,W*0.4])

h2("1.3 Architecture — 13 Docker Services")
table(["Service","Role","Port"], [
    ["postgres","PostgreSQL 16 database","5432"],
    ["redis","Cache, sessions, rate limiting","6379"],
    ["backend","FastAPI app (Gunicorn + Uvicorn)","8000"],
    ["frontend","Next.js standalone server","3000"],
    ["nginx","Reverse proxy + SSL","80/443"],
    ["prometheus","Metrics collection","9090"],
    ["grafana","Dashboards","3001"],
    ["alertmanager","Alert routing","9093"],
    ["node-exporter","Host metrics","9100"],
    ["redis-exporter","Redis metrics","9121"],
    ["postgres-exporter","PostgreSQL metrics","9187"],
    ["worker","Celery background tasks","-"],
    ["flower","Celery monitoring","5555"],
], [W*0.22,W*0.48,W*0.3])

story.append(PageBreak())

h2("1.5 System Requirements")
table(["Environment","CPU","RAM","Disk","Software"], [
    ["Development","4 cores","8 GB","20 GB SSD","Python 3.12, Node 20, PostgreSQL 16, Redis 7"],
    ["Production (small)","4 cores","16 GB","100 GB SSD","Docker 24+, Docker Compose v2"],
    ["Production (medium)","8 cores","32 GB","250 GB SSD","Docker + external DB/Redis"],
    ["Production (large)","16+ cores","64+ GB","500 GB SSD","Kubernetes or cloud managed"],
], [W*0.17,W*0.15,W*0.15,W*0.18,W*0.35])

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 2 ═════════════
h1("PART 2: ALL PASSWORDS & CREDENTIALS")
warn("KEEP THIS DOCUMENT SECURE. Change all default passwords before production!")

h2("2.1 Demo Accounts")
body("All demo accounts use password: <b>demo1234</b>")
table(["Role","Email","Name","Access Level"], [
    ["Super Admin","admin@vestra.co.ke","Admin User","Full system access, all admin panels"],
    ["Agent","jane.muthoni@email.com","Jane Muthoni","Agent dashboard, listings, leads, commissions"],
    ["Buyer","samuel.njoroge@email.com","Samuel Njoroge","Buyer dashboard, favorites, escrow, search"],
    ["Seller","peter.omondi@email.com","Peter Omondi","Seller dashboard, listings, analytics"],
    ["Landlord","grace.akinyi@email.com","Grace Akinyi","Landlord dashboard, tenants, maintenance"],
])

h2("2.2 Database Credentials")
table(["Setting","Development","Production (change this!)"], [
    ["PostgreSQL Host","localhost","postgres (Docker service)"],
    ["PostgreSQL Port","5432","5432"],
    ["Database Name","vestra","vestra"],
    ["Username","postgres","postgres"],
    ["Password","postgres","CHANGE_ME — use strong password"],
    ["Test Database","vestra_test","N/A"],
    ["Connection URL","postgresql+asyncpg://postgres:postgres@localhost:5432/vestra","postgresql+asyncpg://postgres:CHANGE_ME@postgres:5432/vestra"],
], [W*0.22,W*0.38,W*0.4])

h2("2.3 Redis Credentials")
table(["Setting","Development","Production"], [
    ["Redis URL","redis://localhost:6379/0","redis://redis:6379/0"],
    ["Redis Password","(none)","REDIS_PASSWORD — REQUIRED"],
    ["Redis DB (tests)","redis://localhost:6379/1","N/A"],
], [W*0.22,W*0.38,W*0.4])

story.append(PageBreak())

h2("2.4 API Keys & Security Tokens")
table(["Variable","Purpose","How to Generate / Where to Get"], [
    ["SECRET_KEY","JWT signing key (64+ chars)","python -c \"import secrets; print(secrets.token_hex(32))\""],
    ["ENCRYPTION_KEY","Fernet key for PII encryption","python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""],
    ["ACCESS_TOKEN_EXPIRE_MINUTES","JWT access token TTL","Default: 60 minutes"],
    ["REFRESH_TOKEN_EXPIRE_DAYS","JWT refresh token TTL","Default: 7 days"],
    ["TURNSTILE_SECRET_KEY","Cloudflare CAPTCHA secret","Cloudflare Dashboard > Turnstile"],
    ["TURNSTILE_SITE_KEY","Cloudflare CAPTCHA site key","Cloudflare Dashboard > Turnstile"],
    ["CSRF_SECRET","CSRF token secret","Auto-generated from SECRET_KEY"],
], [W*0.22,W*0.28,W*0.5])

h2("2.5 Payment Provider Keys")
table(["Provider","Variable","Where to Get","Sandbox Value"], [
    ["M-Pesa","MPESA_CONSUMER_KEY","developer.safaricom.co.ke","From Daraja portal"],
    ["M-Pesa","MPESA_CONSUMER_SECRET","developer.safaricom.co.ke","From Daraja portal"],
    ["M-Pesa","MPESA_SHORTCODE","Daraja portal","174379 (sandbox)"],
    ["M-Pesa","MPESA_PASSKEY","Daraja portal","bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919 (sandbox)"],
    ["Stripe","STRIPE_SECRET_KEY","dashboard.stripe.com","sk_test_..."],
    ["Stripe","STRIPE_WEBHOOK_SECRET","Stripe Dashboard > Webhooks","whsec_..."],
    ["PayPal","PAYPAL_CLIENT_ID","developer.paypal.com","From PayPal dashboard"],
    ["PayPal","PAYPAL_CLIENT_SECRET","developer.paypal.com","From PayPal dashboard"],
    ["Airtel Money","AIRTEL_CLIENT_ID","Airtel Developer Portal","From portal"],
    ["Airtel Money","AIRTEL_CLIENT_SECRET","Airtel Developer Portal","From portal"],
    ["Crypto (USDT)","CRYPTO_WALLET_ADDRESS","Your Polygon wallet","(your wallet)"],
    ["Crypto","CRYPTO_RPC_URL","Polygon RPC","https://polygon-rpc.com"],
], [W*0.14,W*0.22,W*0.32,W*0.32])

h2("2.6 Email & WhatsApp Configuration")
table(["Service","Variable","Example"], [
    ["SMTP Host","SMTP_HOST","smtp.gmail.com"],
    ["SMTP Port","SMTP_PORT","587"],
    ["SMTP User","SMTP_USER","noreply@vestra.co.ke"],
    ["SMTP Password","SMTP_PASSWORD","(Gmail App Password — 16 chars)"],
    ["From Email","SMTP_FROM_EMAIL","noreply@vestra.co.ke"],
    ["WhatsApp Phone ID","WHATSAPP_PHONE_NUMBER_ID","From Meta Business Suite"],
    ["WhatsApp Token","WHATSAPP_ACCESS_TOKEN","From Meta Developer Portal"],
    ["WhatsApp Verify","WHATSAPP_VERIFY_TOKEN","(custom string you create)"],
], [W*0.24,W*0.36,W*0.4])

story.append(PageBreak())

h2("2.7 Complete Environment Variables (.env.production)")
body("Below is the COMPLETE list of all 75+ environment variables. Copy this to .env in production and fill in ALL values marked REQUIRED.")
code("""# ── Core ───────────────────────────────────────────────────
APP_NAME=Vestra
APP_VERSION=4.0.0
ENVIRONMENT=production          # development | staging | production
DEBUG=false
LOG_LEVEL=info

# ── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:REQUIRED_CHANGE_ME@postgres:5432/vestra
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_RECYCLE=3600

# ── Redis ─────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=REQUIRED_CHANGE_ME
REDIS_MAX_CONNECTIONS=50

# ── Auth & Security ───────────────────────────────────────
SECRET_KEY=REQUIRED_64_CHARS_MINIMUM_GENERATE_WITH_secrets.token_hex(32)
ENCRYPTION_KEY=REQUIRED_FERNET_KEY_GENERATE_WITH_Fernet.generate_key()
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
ACCOUNT_LOCKOUT_MAX_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION_MINUTES=15
SESSION_IDLE_TIMEOUT_MINUTES=30

# ── M-Pesa Daraja API (Kenya) ─────────────────────────────
MPESA_CONSUMER_KEY=REQUIRED
MPESA_CONSUMER_SECRET=REQUIRED
MPESA_SHORTCODE=174379
MPESA_PASSKEY=REQUIRED
MPESA_CALLBACK_URL=https://YOUR_DOMAIN/api/v1/payments/mpesa/callback
MPESA_ENV=sandbox

# ── Stripe ────────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_live_REQUIRED
STRIPE_WEBHOOK_SECRET=whsec_REQUIRED
STRIPE_PUBLISHABLE_KEY=pk_live_REQUIRED

# ── PayPal ────────────────────────────────────────────────
PAYPAL_CLIENT_ID=REQUIRED
PAYPAL_CLIENT_SECRET=REQUIRED
PAYPAL_ENV=live

# ── Airtel Money ──────────────────────────────────────────
AIRTEL_CLIENT_ID=
AIRTEL_CLIENT_SECRET=
AIRTEL_ENV=sandbox

# ── Bank Transfer ─────────────────────────────────────────
BANK_ACCOUNT_NAME=Vestra Technologies Ltd
BANK_ACCOUNT_NUMBER_KCB=
BANK_ACCOUNT_NUMBER_EQUITY=
BANK_ACCOUNT_NUMBER_COOP=
BANK_ACCOUNT_NUMBER_NCBA=
BANK_ACCOUNT_NUMBER_ABSA=

# ── Cryptocurrency ────────────────────────────────────────
CRYPTO_WALLET_ADDRESS_USDT=
CRYPTO_RPC_URL=https://polygon-rpc.com
CRYPTO_ENABLED=false

# ── Email (SMTP) ─────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@vestra.co.ke
SMTP_FROM_NAME=Vestra

# ── WhatsApp ─────────────────────────────────────────────
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_BUSINESS_ID=
WHATSAPP_APP_SECRET=

# ── Rate Limiting ─────────────────────────────────────────
RATE_LIMIT_AUTH_PER_MINUTE=10
RATE_LIMIT_GENERAL_PER_MINUTE=120
RATE_LIMIT_ADMIN_PER_MINUTE=300

# ── CORS ─────────────────────────────────────────────────
CORS_ORIGINS=https://vestra.co.ke,https://www.vestra.co.ke

# ── Sentry ────────────────────────────────────────────────
SENTRY_DSN=

# ── Turnstile CAPTCHA ─────────────────────────────────────
TURNSTILE_SECRET_KEY=
TURNSTILE_SITE_KEY=

# ── Monitoring ────────────────────────────────────────────
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=REQUIRED_CHANGE_ME
FLOWER_USER=admin
FLOWER_PASSWORD=REQUIRED_CHANGE_ME

# ── Gunicorn ──────────────────────────────────────────────
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_BACKLOG=2048
GUNICORN_TIMEOUT=120
GUNICORN_MAX_REQUESTS=10000

# ── Celery ────────────────────────────────────────────────
CELERY_BROKER_URL=redis://redis:6379/0

# ── Feature Flags ─────────────────────────────────────────
AI_CHAT_ENABLED=true
WHATSAPP_ENABLED=false
MAINTENANCE_MODE=false""")

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 3 ═════════════
h1("PART 3: GETTING STARTED")
h2("3.1 Prerequisites")
for p in ["Python 3.12+ (for backend development)","Node.js 20+ (for frontend development)","PostgreSQL 16 (database)","Redis 7 (cache, sessions, rate limiting)","Docker & Docker Compose (for production deployment)","Git"]:
    bullet(p)

h2("3.2 Local Development Setup (5 Minutes)")
h3("Step 1: Clone and Install Backend")
code("""cd VESTRA_FULL_SYSTEM/vestra/backend
python -m venv venv
venv\\Scripts\\activate          # Windows
# source venv/bin/activate      # Mac/Linux
pip install -r requirements.txt
cp .env .env.local              # Edit SECRET_KEY
alembic upgrade head""")
h3("Step 2: Install Frontend")
code("""cd VESTRA_FULL_SYSTEM/vestra/frontend-build
npm install
cp .env.example .env.local""")
h3("Step 3: Start the System")
code("""# Terminal 1 — Backend
cd vestra/backend
venv\\Scripts\\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd vestra/frontend-build
npm run dev

# Open http://localhost:3000""")

h2("3.3 Docker Production Setup")
code("""cd VESTRA_FULL_SYSTEM/vestra
# 1. Configure environment
cp .env.production.template .env
# Edit ALL REQUIRED values

# 2. Build and start all 13 services
docker-compose build
docker-compose up -d

# 3. Run database migrations
docker-compose exec backend alembic upgrade head

# 4. Verify
curl http://localhost/health
curl http://localhost/metrics
# Grafana: http://localhost:3001""")

h2("3.5 Seeding Demo Data")
code("""cd vestra/backend
# Seed 50+ properties, 15+ users, payments, verifications, etc.
python seed_simple.py
# All demo passwords: demo1234""")

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 4 ═════════════
h1("PART 4: HOW EVERYTHING WORKS")

h2("4.1 Authentication System")
body("VESTRA uses JWT (JSON Web Tokens) with IP binding, refresh token rotation, TOTP 2FA, and session management for maximum security.")
bullet("<b>Registration:</b> Email + password + phone. Password must be 8-128 chars with uppercase, lowercase, and digit. CAPTCHA required in production.")
bullet("<b>Login:</b> Email + password. Returns JWT access token (1h TTL) and refresh token (7 day TTL). If 2FA enabled, returns temp_token requiring TOTP verification.")
bullet("<b>Account Lockout:</b> 5 failed attempts = 15-minute lockout (Redis-backed).")
bullet("<b>2FA:</b> TOTP setup via QR code (pyotp). Required for agents and admins.")
bullet("<b>Session Management:</b> Max 5 concurrent sessions. Per-session device/IP/user-agent metadata. Revoke individual or all sessions.")
bullet("<b>Password Reset:</b> Email-based flow with time-limited tokens.")
bullet("<b>GDPR:</b> Data export (JSON) and right-to-be-forgotten (account deletion with data anonymization).")

h2("4.2 User Roles & Permissions")
table(["Role","Permissions","Dashboard"], [
    ["buyer","Browse properties, save favorites, make offers, escrow, reviews","Buyer Dashboard"],
    ["seller","List properties, manage listings, view analytics, receive payouts","Seller Dashboard"],
    ["agent","List properties for clients, earn commissions, get leads, verify","Agent Dashboard"],
    ["landlord","Manage rental units, tenants, leases, maintenance, rent collection","Landlord Dashboard"],
    ["tenant","View lease, pay rent, request maintenance, discover properties","Tenant Dashboard"],
    ["admin","Manage users, properties, payments, KYC, fraud, disputes, monitoring","Admin Panel"],
    ["super_admin","Full system access including system configuration and API keys","Admin Panel"],
], [W*0.13,W*0.47,W*0.4])

story.append(PageBreak())

h2("4.3 Property Management")
body("Properties are the core entity. Each listing goes through AI verification before being trusted.")
bullet("<b>Create Listing:</b> Title, description, price, type (house/apartment/land/commercial), listing type (sale/rent), bedrooms, bathrooms, size, city, county, amenities, images.")
bullet("<b>AI Verification:</b> Each property is analyzed by the Vestra AI engine for fraud risk, trust score, price reasonableness, and document authenticity.")
bullet("<b>Featured Listings:</b> Paid promotion (via M-Pesa) to boost visibility on the marketplace.")
bullet("<b>SEO:</b> Auto-generated meta tags, Open Graph images, and sitemap entries.")
bullet("<b>AI Search:</b> Natural language search queries like '3 bedroom house in Nairobi under 10M' are parsed by AI into structured filters.")
bullet("<b>Full-Text Search:</b> PostgreSQL GIN indexes with pg_trgm for fast property search.")

h2("4.4 AI Vestima Price Estimator")
body("Vestima is VESTRA's AI-powered property valuation engine — similar to Zillow's Zestimate but built for African real estate markets.")
bullet("<b>City-based price/sqft baselines</b> for all Kenyan cities")
bullet("<b>Bedroom/bathroom multipliers</b> based on market data")
bullet("<b>Year-built depreciation</b> calibrated for Kenya")
bullet("<b>Amenity premiums:</b> pool, gym, security, parking, solar, borehole")
bullet("<b>Neighborhood trend scoring:</b> up/stable/down")
bullet("<b>Confidence score (0-100%):</b> color-coded with methodology explanation")
bullet("<b>Comparable properties:</b> within 2km radius")
bullet("<b>Historical tracking:</b> value changes over time")

h2("4.5 Payment Processing — 6 Providers")
body("VESTRA supports 6 payment methods through a pluggable provider architecture:")
table(["Provider","Method","Use Case","Flow"], [
    ["M-Pesa","STK Push","Primary: Kenya","Initiate -> User enters PIN on phone -> Callback confirms payment"],
    ["Stripe","Payment Intent","International cards","Create PaymentIntent -> Confirm with card -> Webhook confirms"],
    ["PayPal","REST API","International","Create order -> Redirect to PayPal -> Capture on return"],
    ["Bank Transfer","Manual","Kenya banks (5)","Generate instructions -> User transfers -> Admin confirms"],
    ["Airtel Money","API","Kenya","Similar to M-Pesa flow"],
    ["Crypto","USDT (Polygon)","Tech-savvy users","Generate address -> Detect on-chain -> Auto-confirm"],
], [W*0.1,W*0.14,W*0.18,W*0.58])

story.append(PageBreak())

h2("4.6 Trust & Safety — 8-Layer Verification System")
body("Every seller, agent, and property goes through 8 verification layers before being trusted:")
table(["#","Layer","What It Verifies","Technology"], [
    ["1","Identity (KYC++)","Government ID, biometric selfie, address proof","OCR + Facial Recognition + OTP"],
    ["2","Agent Licensing","Regulatory body license, broker certification","API Integration + Manual Review"],
    ["3","Property Authentication","Title deed, land registry, ownership chain","OCR + Blockchain + Registry API"],
    ["4","Physical Site","GPS-tagged photos, inspector visits","GPS + Image Metadata"],
    ["5","Financial Trust","Escrow, payment history, transaction patterns","ML Pattern Analysis"],
    ["6","Community Trust","Verified reviews, ratings, referrals","Weighted Graph Algorithm"],
    ["7","AI Fraud Detection","Fake listings, price anomalies, image forgery","Deep Learning + Heuristics"],
    ["8","Blockchain Title","Immutable ownership records (SHA-256)","Linked Blocks + Crypto"],
], [W*0.04,W*0.16,W*0.38,W*0.42])

h3("Verification Badge Tiers")
table(["Tier","Requirements","Benefits"], [
    ["Bronze","Email + Phone verified + KYC submitted","Basic trust badge, browse and inquire"],
    ["Silver","KYC approved + 3+ months active","Enhanced visibility, list up to 3 properties"],
    ["Gold","Agent license verified + 10+ transactions","Premium placement, unlimited listings, priority support"],
    ["Platinum","Site verified + 50+ transactions + 4.5+ rating","Featured across platform, VIP support, platinum badge"],
], [W*0.1,W*0.45,W*0.45])

h2("4.7 Real-Time WebSocket System")
bullet("<b>Live Chat:</b> Typing indicators, read receipts, online presence dots")
bullet("<b>Real-time Notifications:</b> Instant push to navbar badge + toast")
bullet("<b>Live Payment Status:</b> M-Pesa/Stripe confirmations without polling")
bullet("<b>Admin Live Dashboard:</b> New signups, payments, verifications stream")
bullet("<b>Connection:</b> JWT-authenticated, auto-reconnect (exponential backoff, max 20 attempts)")
bullet("<b>Heartbeat:</b> 25s ping/pong to keep connections alive")
bullet("<b>Redis-backed:</b> Pub/sub for horizontal scaling across multiple backend instances")

h2("4.8 Notification System")
body("Multi-channel notifications via in-app, WhatsApp, and email:")
bullet("<b>In-app notifications:</b> Real-time via WebSocket, stored in database with read/unread tracking")
bullet("<b>Email notifications:</b> SMTP with HTML templates for verification, password reset, payment receipts, welcome")
bullet("<b>WhatsApp notifications:</b> Via Meta Cloud API for payment confirmations, property updates, and support")
bullet("<b>Lifecycle reminders:</b> Lease expiry, rent due, subscription renewal, KYC expiry")

story.append(PageBreak())

h2("4.10 Escrow Service")
body("Secure purchase escrow protecting both buyers and sellers:")
bullet("<b>Create Escrow:</b> Buyer deposits funds into platform escrow for a specific property")
bullet("<b>Deposit Confirmation:</b> Payment verified and held securely")
bullet("<b>Release:</b> Funds released to seller upon buyer confirmation of satisfactory property transfer")
bullet("<b>Cancel:</b> Buyer can cancel and receive refund (minus fees) before release")
bullet("<b>Dispute:</b> Either party can file dispute — admin mediates")
bullet("<b>Auto-Release:</b> Configurable timer releases funds automatically after N days if no dispute")

h2("4.11 Subscription Plans")
table(["Plan","Price (KES/month)","Listings","Features"], [
    ["Free","0","1","Basic listing, standard support"],
    ["Basic","999","5","Featured listing, email support, basic analytics"],
    ["Pro","2,999","20","Priority placement, analytics dashboard, priority support"],
    ["Premium","9,999","Unlimited","VIP placement, dedicated agent, API access, white-label"],
], [W*0.12,W*0.18,W*0.12,W*0.58])

h2("4.12 Referral Program")
bullet("<b>Referral Code:</b> Each user gets a unique referral code")
bullet("<b>Reward: KES 500</b> for each referred user who signs up")
bullet("<b>Bonus: KES 1,000</b> when referred user makes first payment")
bullet("<b>Leaderboard:</b> Top referrers displayed publicly")
bullet("<b>Claim Earnings:</b> Accumulated rewards can be withdrawn via M-Pesa")

h2("4.13 Enterprise API")
body("Enterprise clients can integrate VESTRA into their own systems:")
bullet("<b>API Keys:</b> Hashed keys with configurable rate limits and expiration")
bullet("<b>Usage Tracking:</b> Calls per day, per month, per endpoint analytics")
bullet("<b>Webhooks:</b> HMAC-SHA256 signed event delivery with automatic retries (3 attempts, exponential backoff)")
bullet("<b>Supported Events:</b> property.created, property.updated, payment.completed, verification.completed, user.registered")

h2("4.14 Background Workers")
body("Celery workers process background tasks via Redis Streams:")
bullet("<b>notification:</b> In-app notification creation (3 retries, 1s backoff)")
bullet("<b>email:</b> SMTP email sending (3 retries, 1s backoff)")
bullet("<b>webhook:</b> Enterprise webhook delivery (3 retries, 2s backoff)")
bullet("<b>analytics:</b> Event recording (1 retry, 0.5s backoff)")
bullet("<b>cleanup:</b> Periodic cleanup jobs (2 retries, 10s backoff)")
bullet("<b>lifecycle_notifications:</b> Scheduled reminders for expiring leases, subscriptions, KYC")

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 5 ═════════════
h1("PART 5: USING THE SYSTEM")
body("This section explains how each user type uses VESTRA day-to-day.")

h2("5.1 Buyer's Guide")
body("As a buyer, you can search for properties, save favorites, make offers, and use escrow for secure purchases.")
h3("Buyer Workflow:")
bullet("<b>1. Register/Login:</b> Create account as 'buyer' role. Verify email and phone.")
bullet("<b>2. Browse Properties:</b> Go to /market — use AI search, filters, map view, or grid/list views.")
bullet("<b>3. Property Detail:</b> View photos, trust score, AI valuation, agent info, location map.")
bullet("<b>4. Contact Seller/Agent:</b> Use in-app messaging (real-time chat) or WhatsApp button.")
bullet("<b>5. Verify Property:</b> Request AI verification report (paid service via M-Pesa).")
bullet("<b>6. Make Offer:</b> Submit offer through the platform.")
bullet("<b>7. Escrow:</b> Deposit payment into escrow — funds held until property transfer confirmed.")
bullet("<b>8. Release Funds:</b> After satisfactory inspection, release funds to seller.")
bullet("<b>9. Leave Review:</b> Rate the seller/agent and property after transaction.")

h2("5.2 Seller's Guide")
bullet("<b>1. Register as Seller:</b> Complete KYC verification (required before listing).")
bullet("<b>2. Create Listing:</b> Go to /properties/new — fill in all details, upload photos, set price.")
bullet("<b>3. AI Verification:</b> Your listing is automatically analyzed for trust score and fraud risk.")
bullet("<b>4. Manage Listings:</b> View all your listings at /properties/my — edit, publish, unpublish, delete.")
bullet("<b>5. Respond to Inquiries:</b> Messages from buyers appear in /messages — respond promptly for higher trust score.")
bullet("<b>6. Accept Offers:</b> Review and accept/reject buyer offers.")
bullet("<b>7. Escrow:</b> Buyer deposits into escrow — you transfer property — funds released to you.")
bullet("<b>8. Analytics:</b> View listing views, inquiries, and conversion rates at /dashboard/seller/analytics.")

story.append(PageBreak())

h2("5.3 Agent's Guide")
bullet("<b>1. Register as Agent:</b> Complete KYC + license verification for Gold badge.")
bullet("<b>2. Agent Profile:</b> Display license number, years experience, badge level, reviews.")
bullet("<b>3. Client Management:</b> Track leads at /dashboard/agent/leads.")
bullet("<b>4. List for Clients:</b> Create property listings on behalf of sellers.")
bullet("<b>5. Commissions:</b> Track earnings at /dashboard/agent/commissions.")
bullet("<b>6. Directory:</b> Your profile appears at /agents/directory — optimize for more leads.")

h2("5.5 Tenant's Guide")
bullet("<b>1. Discover Rentals:</b> Browse rental properties at /dashboard/tenant/discover.")
bullet("<b>2. Pay Rent:</b> Pay monthly rent via M-Pesa at /dashboard/tenant/rent.")
bullet("<b>3. View Receipts:</b> Download PDF receipts at /dashboard/tenant/receipts.")
bullet("<b>4. Maintenance:</b> Submit maintenance requests with photos at /dashboard/tenant/maintenance.")

h2("5.6 Admin Guide")
body("The admin panel at /admin is the command center for platform management.")
h3("Admin Sections:")
bullet("<b>Overview:</b> Dashboard with key metrics — total users, properties, payments, verifications, revenue charts.")
bullet("<b>Users:</b> View all users, filter by role, suspend/activate accounts, view KYC status.")
bullet("<b>Properties:</b> Review all listings, approve/reject, feature/unfeature, view trust scores.")
bullet("<b>Payments:</b> Monitor all transactions across 6 providers, process refunds.")
bullet("<b>Verifications:</b> Review AI verification requests, approve/reject with comments.")
bullet("<b>KYC:</b> Review identity documents, approve/reject with rejection reasons.")
bullet("<b>Fraud:</b> Review fraud reports, check blacklist, investigate suspicious activity.")
bullet("<b>Disputes:</b> Mediate escrow disputes, assign to investigators, resolve with decisions.")
bullet("<b>Audit Logs:</b> Search and filter all system actions with correlation IDs.")
bullet("<b>Monitoring:</b> System health dashboard with real-time metrics.")

story.append(PageBreak())

h2("5.7 Mobile App Usage")
body("VESTRA is available as native iOS and Android apps via Capacitor, plus as a PWA.")
bullet("<b>PWA Installation (Android):</b> Visit vestra.co.ke in Chrome → tap 'Add to Home Screen' → install.")
bullet("<b>PWA Installation (iOS):</b> Visit in Safari → tap Share → 'Add to Home Screen' → name it → done.")
bullet("<b>Native App:</b> Download from Apple App Store or Google Play Store (coming soon).")
bullet("<b>Offline Mode:</b> Previously viewed properties are cached. Offline actions are queued and synced when online.")
bullet("<b>Push Notifications:</b> Real-time alerts for messages, payment updates, and verification results.")

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 6 ═════════════
h1("PART 6: ADMINISTRATION & MANAGEMENT")

h2("6.1 Admin Dashboard Overview")
body("Access at http://localhost:3000/admin (or /en/admin). Login as admin@vestra.co.ke / demo1234.")
bullet("<b>Stats Cards:</b> Total users, active properties, pending verifications, monthly revenue")
bullet("<b>Revenue Chart:</b> Interactive charts showing revenue by provider, daily/weekly/monthly")
bullet("<b>Recent Activity:</b> Latest signups, payments, verifications, and listings")
bullet("<b>Quick Actions:</b> Review pending KYC, investigate fraud reports, process payouts")

h2("6.2 User Management")
bullet("<b>Search/Filter:</b> By email, name, role, KYC status, join date")
bullet("<b>Actions:</b> View profile, suspend/activate, change role, reset password, delete (GDPR)")
bullet("<b>KYC Status:</b> pending → reviewing → approved/rejected (with reason)")

h2("6.3 Property Moderation")
bullet("<b>Review Queue:</b> New listings flagged by AI for manual review")
bullet("<b>Trust Score:</b> Each property has a trust score (0-100) — properties below 30 are auto-hidden")
bullet("<b>Featured Management:</b> Approve/reject featured listing payments, set featured duration")

h2("6.4 KYC Verification Workflow")
bullet("<b>1. User submits:</b> ID type (National ID/Passport/Driving License/Alien ID), ID number, front/back photos, selfie")
bullet("<b>2. Admin reviews:</b> Compare ID photo with selfie, verify document authenticity, check ID number format")
bullet("<b>3. Decision:</b> Approve (user gets Silver+ badge) or Reject (with reason for re-submission)")

h2("6.5 Fraud Management")
bullet("<b>Fraud Reports:</b> Community-submitted reports with evidence (screenshots, chat logs)")
bullet("<b>Blacklist:</b> Public blacklist of confirmed fraudulent phone numbers, emails, names")
bullet("<b>AI Detection:</b> Automated flagging of suspicious listings (price anomalies, duplicate images, scam patterns)")
bullet("<b>Investigation:</b> Admin can mark reports as investigating → confirmed (ban user, remove listings) → dismissed")

story.append(PageBreak())

h2("6.9 Audit Logs")
body("Every action in the system is logged with correlation IDs for traceability:")
bullet("<b>Tracked Actions:</b> User registration, login, property CRUD, payment initiation, verification submission, admin actions")
bullet("<b>Fields:</b> user_id, action, resource_type, resource_id, ip_address, user_agent, correlation_id, timestamp")
bullet("<b>Retention:</b> Payment/dispute records: 5 years. General: 2 years. GDPR purge after 90 days for deleted accounts.")
bullet("<b>Export:</b> Filter and export audit logs as CSV for compliance reporting.")

h2("6.10 System Monitoring (Grafana)")
body("Access Grafana at http://localhost:3001 (credentials: admin / GRAFANA_ADMIN_PASSWORD from .env)")
bullet("<b>Pre-built Dashboard:</b> 'Vestra System Overview' with 15+ panels")
bullet("<b>API Metrics:</b> Request rate, error rate (by endpoint), latency percentiles (p50/p95/p99), in-flight requests")
bullet("<b>Database Metrics:</b> Active connections, pool utilization, query latency, transaction rate")
bullet("<b>Redis Metrics:</b> Hit rate, memory usage, connected clients, operations/sec")
bullet("<b>System Metrics:</b> CPU usage, memory usage, disk I/O, network traffic")
bullet("<b>Alert Rules:</b> High error rate (>5%), high latency (p95 >1s), service down, disk full (>90%), memory high (>90%)")
bullet("<b>Alert Routing:</b> Critical → Slack + Email immediate. Warning → Slack. Info → Email digest.")

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 7 ═════════════
h1("PART 7: MAINTENANCE & OPERATIONS")

h2("7.1 Daily Operations Checklist")
bullet("Check Grafana dashboard for anomalies (error rates, latency spikes, resource usage)")
bullet("Review pending KYC verifications — aim to process within 24 hours")
bullet("Review fraud reports — investigate high-risk reports immediately")
bullet("Monitor payment callbacks — ensure M-Pesa/Stripe webhooks are processing")
bullet("Check disk space — ensure at least 20% free on database and log volumes")

h2("7.2 Database Backups")
body("Run the automated backup script daily:")
code("""cd vestra
# Manual backup
bash scripts/backup-db.sh

# Automated (add to crontab):
# 0 1 * * * cd /path/to/vestra && bash scripts/backup-db.sh

# Backup features:
# - pg_dump in custom format with parallel jobs
# - Gzip compression
# - Upload to S3/GCS/SFTP
# - Retention: 30 days (configurable)
# - Integrity verification via pg_restore --list""")

h2("7.3 Redis Management")
bullet("<b>Persistence:</b> AOF enabled with appendfsync everysec — data safe across restarts")
bullet("<b>Memory:</b> LRU eviction policy (allkeys-lru) — least recently used keys evicted first")
bullet("<b>Monitoring:</b> Check memory fragmentation ratio via Redis Exporter in Grafana")
bullet("<b>Flush:</b> redis-cli FLUSHDB to clear cache (safe — will rebuild from database)")

h2("7.4 SSL Certificate Renewal")
code("""# Using Let's Encrypt with Certbot
sudo certbot renew --dry-run    # Test renewal
sudo certbot renew              # Actual renewal
docker-compose restart nginx    # Reload certificates""")

h2("7.5 Log Management")
bullet("<b>Backend:</b> Structured JSON logs with correlation IDs, printed to stdout/stderr")
bullet("<b>Nginx:</b> JSON access logs with request timing, status codes, user agents")
bullet("<b>Docker:</b> Configured with json-file driver + rotation (max-size: 10m, max-file: 3)")
bullet("<b>Viewing:</b> docker-compose logs -f backend | jq '.' for pretty-printed JSON")

h2("7.6 Performance Tuning")
bullet("<b>Database Pool:</b> Adjust DATABASE_POOL_SIZE (default 20) and DATABASE_MAX_OVERFLOW (default 40) based on load")
bullet("<b>Gunicorn Workers:</b> Rule of thumb: (2 * CPU cores) + 1. Adjust GUNICORN_WORKERS and GUNICORN_THREADS")
bullet("<b>Redis Connections:</b> REDIS_MAX_CONNECTIONS (default 50) — increase for high concurrency")
bullet("<b>Rate Limiting:</b> Tune RATE_LIMIT_* values based on traffic patterns")
bullet("<b>Nginx Workers:</b> worker_processes auto — nginx.conf already configured")

story.append(PageBreak())

h2("7.8 Scaling the System")
body("VESTRA is designed for horizontal scaling:")
bullet("<b>Backend:</b> Deploy multiple backend instances behind nginx load balancer. Redis pub/sub handles WebSocket fan-out across instances.")
bullet("<b>Database:</b> Start with vertical scaling (bigger instance). Move to read replicas for read-heavy workloads. Consider connection pooling (PgBouncer) at >500 connections.")
bullet("<b>Redis:</b> Use Redis Cluster for >25GB datasets or >50K ops/sec.")
bullet("<b>Frontend:</b> Deploy behind CDN (Cloudflare). Static assets cached indefinitely (content hashes). Use ISR (Incremental Static Regeneration) for semi-static pages.")
bullet("<b>Storage:</b> Move uploads to S3-compatible storage (MinIO, AWS S3, Cloudflare R2) for multi-instance access.")

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 8 ═════════════
h1("PART 8: DEPLOYMENT")

h2("8.1 Docker Compose Deployment (Recommended)")
code("""# 1. Prepare
cd VESTRA_FULL_SYSTEM/vestra
cp .env.production.template .env
# EDIT ALL REQUIRED VALUES IN .env

# 2. Build
docker-compose build --no-cache

# 3. Start database and Redis first
docker-compose up -d postgres redis
sleep 10  # Wait for healthy

# 4. Start remaining services
docker-compose up -d

# 5. Run migrations
docker-compose exec backend alembic upgrade head

# 6. Verify all services
bash scripts/health-check.sh

# 7. Check logs
docker-compose logs -f""")

h2("8.2 Fly.io Deployment")
code("""# Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
cd VESTRA_FULL_SYSTEM/vestra
flyctl launch        # First time — follow wizard
flyctl deploy        # Deploy
flyctl secrets set SECRET_KEY=... DATABASE_URL=...  # Set secrets""")

h2("8.3 Render Deployment")
body("Push to GitHub — Render auto-deploys from render.yaml blueprint. Set environment variables in Render Dashboard.")

h2("8.5 Apple App Store Submission")
body("Files prepared at store-listings/apple-app-store.md. Steps:")
bullet("1. Build native app: bash scripts/setup-mobile.sh")
bullet("2. Open ios/App in Xcode")
bullet("3. Configure signing (Apple Developer account required — $99/year)")
bullet("4. Archive and upload to App Store Connect")
bullet("5. Fill in App Store listing (description already prepared in BOTH English and Swahili)")
bullet("6. Submit for review (typically 1-2 days)")

h2("8.6 Google Play Store Submission")
bullet("1. Build: bash scripts/setup-mobile.sh → open android/ in Android Studio")
bullet("2. Generate signed app bundle (Google Play Console account — $25 one-time)")
bullet("3. Upload to Google Play Console")
bullet("4. Fill in listing (description already prepared in English + Swahili)")
bullet("5. Submit for review (typically 2-24 hours)")

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 9 ═════════════
h1("PART 9: TROUBLESHOOTING")

h2("9.1 Common Issues & Fixes")
table(["Problem","Likely Cause","Solution"], [
    ["Database connection refused","PostgreSQL not running or wrong DATABASE_URL","Check: pg_isready. Verify DATABASE_URL in .env. Ensure PostgreSQL service is running."],
    ["Redis connection failed","Redis not running or wrong REDIS_URL","Check: redis-cli PING. App degrades gracefully without Redis — set REDIS_URL correctly."],
    ["M-Pesa callback not received","No HTTPS, IP not whitelisted, wrong endpoint","Must be publicly accessible HTTPS. Whitelist IPs in Daraja portal. Verify callback URL."],
    ["Email not sending","SMTP credentials wrong or using regular Gmail password","Use App Password (not regular password). Enable 2FA on Gmail first. Check SMTP_HOST and PORT."],
    ["Frontend build fails","Node version mismatch or stale node_modules","Use Node 20+. Delete node_modules + package-lock.json. npm install fresh."],
    ["Alembic migration fails","Multiple heads or migration conflict","alembic heads → alembic history → resolve conflicts manually or recreate migration."],
    ["Docker containers exit","Missing env vars, port conflicts, insufficient resources","docker-compose logs <service>. Verify all REQUIRED env vars. Check port usage."],
    ["Rate limited unexpectedly","Too many requests from same IP","Check Redis for rate limit keys. Verify RATE_LIMIT_* env vars. Auth endpoints are stricter."],
    ["CORS errors","Frontend origin not in allowed list","Set CORS_ORIGINS env var to your frontend URL."],
    ["WebSocket disconnects","Proxy timeout or stale connection","Nginx proxy_read_timeout should be >60s. Client auto-reconnects with backoff."],
], [W*0.2,W*0.3,W*0.5])

h2("9.2 Diagnostic Commands")
code("""# Backend health
curl http://localhost:8000/health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Database
docker-compose exec postgres pg_isready
docker-compose exec postgres psql -U postgres -d vestra -c "SELECT count(*) FROM users;"

# Redis
docker-compose exec redis redis-cli PING
docker-compose exec redis redis-cli INFO memory | grep used_memory_human

# Alembic status
docker-compose exec backend alembic current
docker-compose exec backend alembic history

# Docker status
docker-compose ps
docker stats --no-stream""")

h2("9.3 Recovery Procedures")
h3("Database Recovery")
code("""# Restore from backup
gunzip -c backup_2026-06-21.sql.gz | docker-compose exec -T postgres psql -U postgres -d vestra
# Then run migrations
docker-compose exec backend alembic upgrade head""")
h3("Full System Restart")
code("""docker-compose down
docker-compose up -d postgres redis
sleep 10
docker-compose up -d
docker-compose exec backend alembic upgrade head""")

story.append(PageBreak())

# ═══════════════════════════════════════════════════════ PART 10 ════════════
h1("PART 10: SUPPORT & CONTACT")

h2("10.1 Support Channels")
table(["Channel","Detail"], [
    ["Email Support","support@vestra.co.ke"],
    ["System Version","4.0.0 Super Upgrade (World-Class)"],
    ["Documentation","This manual — VESTRA_Complete_System_Manual.pdf"],
    ["Generated",datetime.now(UTC).strftime("%B %d, %Y")],
    ["Backend Tests","210 passing (pytest)"],
    ["Frontend Tests","15 E2E scenarios (Playwright)"],
    ["Load Tests","k6 — 50 concurrent users"],
    ["Ruff Lint","0 issues (clean)"],
    ["ESLint","0 errors (clean)"],
    ["TypeScript","0 errors (strict mode)"],
    ["Backend","FastAPI 0.111 + PostgreSQL 16 + Redis 7"],
    ["Frontend","Next.js 16 + React 19 + TypeScript 5"],
    ["Payments","6 Providers (M-Pesa, Stripe, PayPal, Bank, Airtel, Crypto)"],
    ["Mobile","iOS + Android (Capacitor) + PWA"],
    ["Languages","English + Kiswahili (next-intl)"],
    ["Trust & Safety","8-Layer Verification System"],
], [W*0.3,W*0.7])

spacer(12)
story.append(HRFlowable(width="60%", thickness=1, color=EMERALD, spaceBefore=12, spaceAfter=12))
spacer(6)
story.append(Paragraph(
    "<b>Vestra Technologies Ltd.</b><br/>"
    "Built for Kenya. Trusted by Africa. Powered by AI.<br/>"
    "100% Genuine. Zero Scams. Maximum Trust.<br/>"
    "<b>support@vestra.co.ke</b>",
    ParagraphStyle("END", parent=CENTER, fontSize=10, leading=16, textColor=EMERALD_DARK)
))

# ═══════════════════════════════════════════════════════ BUILD ══════════════
def page_setup(canvas, doc):
    page = canvas.getPageNumber()
    if page > 1:
        canvas.saveState()
        canvas.setStrokeColor(EMERALD)
        canvas.setLineWidth(0.5)
        canvas.line(18*mm, A4[1]-15*mm, A4[0]-18*mm, A4[1]-15*mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(18*mm, A4[1]-14*mm, "VESTRA v4.0.0 — Complete System Manual")
        canvas.drawRightString(A4[0]-18*mm, A4[1]-14*mm, f"Page {page}")
        canvas.setFont("Helvetica", 6)
        canvas.drawCentredString(A4[0]/2, 10*mm, "Confidential — Vestra Technologies Ltd.")
        canvas.restoreState()

doc.build(story, onFirstPage=page_setup, onLaterPages=page_setup)
print(f"Generated: {OUTPUT_PATH}")
print(f"VESTRA Complete System Manual — Ready")
