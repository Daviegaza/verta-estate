# VESTRA — AI-Powered Property Trust Platform

> **Trust Every Property.** Africa's most trusted AI-powered real estate operating system.
> Built in Kenya. Ready for the world. Scaled for millions.

---

## 🏗️ System Architecture

```
vestra/
├── backend/                       # Python FastAPI backend (production-ready)
│   ├── app/
│   │   ├── api/routes/            # REST API endpoints
│   │   │   ├── auth.py            # Register, login, JWT, password reset, email verify
│   │   │   ├── properties.py      # CRUD + AI search + full-text search
│   │   │   ├── verification.py    # AI trust engine
│   │   │   ├── payments.py        # M-Pesa + Stripe
│   │   │   ├── admin.py           # Admin panel APIs
│   │   │   └── ai_routes.py       # AI valuation + market insights
│   │   ├── ai/                    # Built-in AI engine (no external APIs)
│   │   │   └── engine.py          # Fraud detection, trust scoring, valuation, search
│   │   ├── core/
│   │   │   ├── config.py          # Settings with env validation
│   │   │   ├── database.py        # PostgreSQL async with connection pooling
│   │   │   ├── redis.py           # Redis caching, rate limiting, sessions
│   │   │   ├── security.py        # JWT + bcrypt + RBAC
│   │   │   ├── middleware.py       # Rate limiting, logging, compression, CSP
│   │   │   ├── metrics.py         # Prometheus metrics
│   │   │   ├── indexes.py         # Performance + FTS indexes
│   │   │   └── gunicorn_conf.py   # Production WSGI config
│   │   ├── models/                # SQLAlchemy ORM models
│   │   │   ├── user.py, property.py, document.py, payment.py, audit_log.py
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   └── services/
│   │       ├── ai_service.py, property_service.py, search_service.py
│   │       ├── verification_service.py, payment_service.py
│   │       ├── mpesa_service.py, valuation_service.py
│   │       ├── user_service.py, email_service.py, audit_service.py
│   ├── alembic/                   # Database migrations
│   ├── requirements.txt
│   ├── Dockerfile (multi-stage, production)
│   └── .env
│
├── frontend-build/                # Next.js 16 TypeScript React
│   ├── app/ (pages: market, verify, dashboard, admin, auth, properties)
│   ├── components/ (ui, layout, property, verify)
│   ├── hooks/ (useApi, useDebounce, useMediaQuery)
│   ├── lib/ (api.ts with retry, utils.ts)
│   ├── store/ (Zustand auth)
│   └── types/
│
└── docker-compose.yml             # Full stack: Postgres + Redis + Backend + Frontend
```

---

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Python 3.12+
- PostgreSQL 16+
- Redis 7+

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # edit with your keys
uvicorn app.main:app --reload --port 8000
```

API Docs: http://localhost:8000/docs
Metrics: http://localhost:8000/metrics

### 2. Frontend

```bash
cd frontend-build
npm install
cp .env.local.example .env.local  # set NEXT_PUBLIC_API_URL
npm run dev
```

Frontend: http://localhost:3000

### 3. Docker (Production)

```bash
# Set secrets
export POSTGRES_PASSWORD=secure_password
export SECRET_KEY=$(openssl rand -base64 64)
export MPESA_CONSUMER_KEY=...
export MPESA_CONSUMER_SECRET=...
export MPESA_PASSKEY=...
export SMTP_HOST=...
export SMTP_USER=...
export SMTP_PASSWORD=...

docker-compose up -d
```

---

## 🛡️ Production Features (v2.0)

| Capability | Implementation |
|------------|----------------|
| **Caching** | Redis with LRU eviction, 2-min property search cache |
| **Rate Limiting** | Redis sliding-window per endpoint type |
| **Full-Text Search** | PostgreSQL tsvector/tsquery with GIN index |
| **Security Headers** | CSP, HSTS, X-Frame-Options, Permissions-Policy |
| **Compression** | Gzip for responses >1KB |
| **Monitoring** | Prometheus metrics, structured JSON logging, correlation IDs |
| **Health Checks** | /health (detailed), /health/live, /health/ready (K8s) |
| **Error Handling** | Global exception handlers, consistent error format |
| **Email** | SMTP with templates for verification, password reset, welcome |
| **Audit Logging** | All state changes tracked to audit_logs table |
| **Connection Pooling** | Configurable DB pool (20+40 overflow) + Redis pool (50) |
| **Migrations** | Alembic with async support |
| **Auth** | JWT with email verification, password reset, refresh tokens |
| **RBAC** | 6 roles: buyer, seller, agent, landlord, admin, super_admin |
| **File Upload** | Type + size validation, organized per property |

---

## 💰 Revenue Model

| Stream | Amount | Trigger |
|--------|--------|---------|
| Verification Report | KES 500 | Buyer requests AI report |
| Agent Verified Badge | KES 5,000/month | Agent subscribes |
| Listing Fee | KES 500–2,000 | Seller lists property |
| Transaction Fee | 2–3% | Sale/rental completed |
| Premium Subscription | KES 999–4,999/month | Power users |
| Enterprise API | Custom | Banks/Gov agencies |

---

## 🤖 AI Engine (Built-in — No External APIs)

1. **Fraud Detection** — Keyword analysis + price sanity + document checks + agent verification
2. **Trust Score** — Composite 0-100 with ownership confidence and recommendation
3. **Natural Language Search** — "2br Karen under 40k" → structured query filters
4. **Property Valuation** — Market-based estimate with investment score
5. **Market Intelligence** — City-level trends and investor tips

The engine has Kenya-specific knowledge: EARB licensing, title deed formats, riparian land risks, KRA PIN requirements, common scams.

---

## 📊 Database

### Core Tables
- `users` — Accounts with roles and verification status
- `properties` — Listings with trust scores and FTS index
- `agent_profiles` — Agent badges & subscriptions
- `documents` — Title deeds, agreements
- `verifications` — AI analysis results
- `payments` — M-Pesa + Stripe records
- `audit_logs` — Full audit trail

### Performance Indexes
- 25+ targeted B-tree indexes for common queries
- GIN index for full-text search (`idx_properties_fts`)
- Composite indexes for filtered listing queries

---

## 🛣️ Roadmap

### Phase 1 — MVP ✅
- [x] User auth (register/login/JWT/email verify/password reset)
- [x] Property listings (CRUD + full-text search + AI search)
- [x] AI property verification (fraud + trust scores)
- [x] M-Pesa payment integration
- [x] Admin dashboard with analytics
- [x] Redis caching + rate limiting
- [x] Prometheus metrics + structured logging
- [x] Audit logging

### Phase 2 — Growth (Next)
- [ ] Document OCR (title deed extraction)
- [ ] Rent collection via M-Pesa recurring
- [ ] Tenant screening AI
- [ ] WhatsApp Business API integration
- [ ] Property analytics reports

### Phase 3 — Scale
- [ ] Fractional property investment
- [ ] Mortgage partner integrations
- [ ] Kenya Land Registry API integration
- [ ] Mobile app (Flutter)
- [ ] Multi-country expansion

---

## 📞 Support

- Email: support@vestra.co.ke
- WhatsApp: +254 XXX XXX XXX
- Docs: https://docs.vestra.co.ke

---

*Built with ❤️ in Nairobi, Kenya. Serving millions across Africa.*
