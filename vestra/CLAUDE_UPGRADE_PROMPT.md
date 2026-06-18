# VESTRA — Ultimate System Upgrade Prompt

Copy and paste this entire prompt into a fresh Claude conversation to get the full VESTRA upgrade implemented.

---

You are building the world's #1 AI-powered property trust platform for Africa. This is a real production system — not a demo, not a prototype. Every line you write must be production-quality with proper error handling, type safety, security, and testability.

## YOUR CONTEXT

You are working on VESTRA, a FastAPI + Next.js 16 (App Router) + PostgreSQL 16 + Redis 7 platform. The system already has:

- 45+ API endpoints across 15 route modules
- 11 services (auth, payments, properties, verification, whatsapp, rentals, etc.)
- 7 AI sub-engines (fraud detection, trust scoring, valuation, search parsing, etc.)
- 6 middleware layers (rate limiting, CSP, gzip, logging, metrics, security headers)
- M-Pesa + Stripe + WhatsApp Business API integration
- PWA support with service worker + manifest + offline fallback
- 27+ database models (users, properties, verifications, payments, subscriptions, rentals, KYC, messaging, enterprise, analytics, trust/safety)
- Zustand auth store with localStorage persistence
- Axios API client with retry logic + correlation IDs
- 14 frontend components (Button, Input, Card, PropertyCard, etc.)
- 13 pages (market, verify, dashboard, admin, auth, properties)
- Prometheus metrics, structured JSON logging, Sentry-ready

Full tech stack: FastAPI 0.111, Next.js 16.2.9, React 19.2, PostgreSQL 16, Redis 7, Tailwind CSS, Docker, Python 3.12, TypeScript 5.

## FILES YOU MUST READ FIRST

```
vestra/backend/app/core/config.py
vestra/backend/app/ai/engine.py
vestra/backend/app/services/payment_service.py
vestra/backend/app/services/verification_service.py
vestra/backend/app/services/mpesa_service.py
vestra/backend/app/services/subscription_service.py
vestra/backend/app/models/kyc_notification.py
vestra/backend/app/models/enterprise.py
vestra/backend/app/models/rental.py
vestra/backend/app/models/trust_safety.py
vestra/backend/app/models/analytics.py
vestra/backend/app/api/__init__.py
vestra/backend/app/api/routes/payments.py
vestra/frontend-build/lib/api.ts
vestra/frontend-build/types/index.ts
vestra/frontend-build/store/authStore.ts
vestra/frontend-build/app/layout.tsx
```

## CRITICAL SECURITY FIXES (implement these FIRST in every task)

1. `/api/payments/mpesa/callback` — MUST verify Safaricom IP ranges before processing. Add IP whitelist.
2. `/api/whatsapp/broadcast` — MUST use `get_current_admin` not `get_current_user`.
3. `/api/ai/*` endpoints — MUST require authentication (`get_current_user`).
4. All `Float` money fields must use `Numeric(12,2)` instead across ALL models.
5. Every SQL query must use parameterized queries (SQLAlchemy ORM or raw SQL with `:param` syntax).
6. Docker Compose must not have hardcoded secrets — require env vars.

## CODING CONVENTIONS

### Backend (Python/FastAPI)
- All route handlers are `async def` with `Depends(get_db)` for database access
- Services are async wrappers around synchronous logic
- AI engine calls MUST use `asyncio.get_event_loop().run_in_executor(None, sync_fn, ...)` to avoid blocking the event loop
- M-Pesa access token caching uses module-level dict + asyncio.Lock (already implemented in mpesa_service.py)
- All services import from `app.core.config import settings`
- Error format: `{"error": "error_code", "message": "human readable", "path": "...", "correlation_id": "..."}`
- Log format: JSON string with event field: `logger.info('{"event":"user_registered","user_id":%d}', user_id)`

### Frontend (Next.js/React/TypeScript)
- Components use `'use client'` directive for interactivity
- All API calls go through `api` singleton from `@/lib/api`
- Auth state via `useAuthStore` from `@/store/authStore`
- Tailwind CSS classes using `cn()` utility from `@/lib/utils`
- Loading states: `<Spinner />` from `@/components/ui/card`
- Props: TypeScript interfaces in component file or `@/types`
- State: `useState` for local, `useApi` hook for API calls with loading/error/cache
- Every page must handle: loading state, empty state, error state, and success state

## PROJECT STRUCTURE

```
vestra/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, middleware, exception handlers
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   └── engine.py              # VestraAI + 7 sub-engines (1004 lines) — RULE-BASED
│   │   ├── api/
│   │   │   ├── __init__.py             # Router aggregation — ADD NEW ROUTES HERE
│   │   │   └── routes/
│   │   │       ├── auth.py, otp_auth.py
│   │   │       ├── properties.py
│   │   │       ├── verification.py
│   │   │       ├── payments.py
│   │   │       ├── admin.py
│   │   │       ├── ai_routes.py
│   │   │       ├── whatsapp.py
│   │   │       ├── subscriptions.py, rentals.py
│   │   │       ├── kyc.py, notifications.py, messages.py
│   │   │       ├── fraud.py, favorites.py
│   │   │       └── (NEW) reports.py, enterprise.py, escrow.py, disputes.py, reviews.py, webhooks.py
│   │   ├── core/
│   │   │   ├── config.py, database.py, redis.py, security.py
│   │   │   ├── middleware.py, metrics.py, indexes.py, gunicorn_conf.py
│   │   ├── models/
│   │   │   ├── __init__.py             # EXPORTS ALL MODELS — ADD NEW ONES HERE
│   │   │   ├── user.py, property.py, document.py, payment.py
│   │   │   ├── subscription.py, referral.py, title_chain.py, audit_log.py
│   │   │   ├── rental.py, kyc_notification.py, trust_safety.py, enterprise.py, analytics.py
│   │   ├── schemas/
│   │   │   ├── user.py, property.py, verification.py
│   │   ├── services/
│   │   │   ├── ai_service.py, user_service.py, property_service.py
│   │   │   ├── search_service.py, verification_service.py
│   │   │   ├── payment_service.py, mpesa_service.py, valuation_service.py
│   │   │   ├── email_service.py, audit_service.py, whatsapp_service.py
│   │   │   ├── subscription_service.py, rental_service.py
│   │   │   ├── (NEW) kyc_service.py, notification_service.py, messaging_service.py
│   │   │   ├── (NEW) escrow_service.py, dispute_service.py, fraud_service.py
│   │   │   ├── (NEW) report_service.py, receipt_service.py, coupon_service.py
│   │   │   ├── (NEW) payout_service.py, api_key_service.py, webhook_service.py
│   │   │   └── (NEW) search_alert_service.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── alembic/
│   └── seed.py
│
├── frontend-build/
│   ├── app/
│   │   ├── layout.tsx, page.tsx (landing), globals.css
│   │   ├── market/page.tsx, verify/page.tsx, dashboard/page.tsx
│   │   ├── admin/page.tsx, admin/layout.tsx, admin/login/page.tsx
│   │   ├── auth/login/page.tsx, auth/register/page.tsx, auth/forgot-password/page.tsx
│   │   ├── account/page.tsx, agents/page.tsx, subscription/page.tsx
│   │   ├── messages/page.tsx
│   │   ├── properties/[id]/page.tsx, properties/edit/[id]/page.tsx
│   │   ├── properties/my/page.tsx, properties/new/page.tsx
│   │   └── (NEW PAGES — see below)
│   ├── components/
│   │   ├── layout/ (navbar, AuthGuard, AuthInit, ErrorBoundary, PWAInstallPrompt, ServiceWorkerRegister)
│   │   ├── ui/ (button, input, card, toaster)
│   │   ├── property/ (PropertyCard, ValuationWidget)
│   │   └── verify/ (TrustScoreCard)
│   ├── hooks/ (useApi, useDebounce, useMediaQuery)
│   ├── lib/ (api.ts — 40+ methods, utils.ts)
│   ├── store/ (authStore.ts)
│   ├── types/ (index.ts — all TypeScript interfaces)
│   └── public/ (manifest.json, sw.js, offline.html)
```

## INTEGRATION CONTRACTS (DO NOT BREAK THESE)

### API Response Shapes

```typescript
// Property
interface Property {
  id: number; owner_id: number; title: string; description?: string;
  property_type: string; listing_type: string; status: string;
  address: string; city: string; county: string; country: string;
  latitude?: number; longitude?: number;
  price: number; currency: string; price_negotiable: boolean;
  bedrooms?: number; bathrooms?: number; size_sqft?: number; year_built?: number;
  amenities: string[]; images: string[];
  trust_score?: number; is_verified: boolean;
  verification_badge?: 'bronze' | 'silver' | 'gold' | 'platinum';
  views: number; inquiries: number;
  created_at: string; updated_at?: string;
}

// Verification
interface Verification {
  id: number; property_id?: number;
  status: 'pending' | 'in_progress' | 'approved' | 'flagged' | 'rejected';
  fraud_risk_score?: number; trust_score?: number;
  price_reasonableness?: 'under' | 'fair' | 'over';
  ownership_confidence?: 'low' | 'medium' | 'high';
  ai_recommendation?: 'approve' | 'review' | 'reject';
  document_flags: string[]; ai_summary?: string;
  report_url?: string; created_at: string; updated_at?: string;
}

// Payment
interface Payment {
  id: number; amount: number; currency: string;
  method: 'mpesa' | 'stripe' | 'bank_transfer';
  purpose: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'refunded';
  reference?: string; mpesa_checkout_request_id?: string;
  created_at: string;
}

// Admin Stats
interface AdminStats {
  total_users: number; total_properties: number;
  total_verifications: number; total_revenue: number;
  pending_verifications: number; active_listings: number;
  verified_properties: number; agents_count: number;
  charts: {
    monthly_revenue: ChartDataPoint[];
    monthly_listings: ChartDataPoint[];
    monthly_verifications: ChartDataPoint[];
    user_growth: ChartDataPoint[];
    user_distribution: DistributionItem[];
    property_types: DistributionItem[];
    city_distribution: DistributionItem[];
  };
  recent_users: RecentUser[];
  recent_properties: RecentProperty[];
  pending_reviews: PendingReview[];
}
```

### Frontend API Client (in `lib/api.ts`)
ALL existing methods must remain unchanged. Add new methods following this pattern:
```typescript
async newMethod(params): Promise<ReturnType> {
  return withRetry(async () => {
    const res = await this.client.get<ReturnType>('/api/endpoint', { params });
    return res.data;
  });
}
```

### Frontend Routes
```
EXISTING (DO NOT BREAK):
/ → landing page
/market → property marketplace
/verify → AI verification page
/dashboard → user dashboard
/admin → admin dashboard
/admin/login → admin login
/auth/login → sign in
/auth/register → registration
/auth/forgot-password → password reset
/properties/new → create listing
/properties/[id] → property detail
/properties/my → my listings
/properties/edit/[id] → edit listing
/agents → agent directory
/account → account settings
/subscription → plan selection
/messages → messaging inbox

NEW ROUTES TO BUILD:
/agents/[id] → agent profile page
/dashboard/landlord → landlord dashboard (units, tenants, rent)
/dashboard/agent → agent dashboard (listings, leads, earnings)
/admin/verifications → verification review queue
/admin/kyc → KYC review queue
/admin/disputes → dispute management
/admin/fraud → fraud investigation
/admin/enterprise → enterprise API management
/enterprise → enterprise documentation
/enterprise/keys → API key management
/settings → profile settings
/settings/security → security (password, 2FA)
/settings/kyc → KYC verification
/settings/notifications → notification preferences
/properties/compare → property comparison
/properties/[id]/report → trust report view
/wallet → payment history
/wallet/payouts → withdrawal management
/subscription/manage → manage subscription
```

### Database Model Locations
- `kyc_notification.py` → KYCVerification, KYCStatus, Notification, Message, SavedProperty, SavedSearch
- `enterprise.py` → APIKey, Webhook, WebhookEvent, Coupon, DiscountType, Payout, PayoutStatus, RentReceipt, InspectionReport, InspectionType
- `analytics.py` → UserEvent, PriceChange, VerificationOutcome, SearchAnalytics
- `trust_safety.py` → Review, EscrowTransaction, EscrowStatus, Dispute, DisputeStatus, FraudReport, FraudReportStatus

### Route Registration (in `api/__init__.py`)
Each new route module must be imported and included in `api_router`:
```python
from app.api.routes.new_module import router as new_router
api_router.include_router(new_router)
```

### Model Registration (in `models/__init__.py`)
Each new model class must be imported and added to `__all__`.

---

## PRIORITY TASK LIST (7 Phases — Complete in Order)

### PHASE 1: SECURITY & STABILITY (Days 1-3)
**Goal: Platform is secure against attacks, no critical vulnerabilities**

1. Verify M-Pesa callback has Safaricom IP whitelist active in `api/routes/payments.py`
2. Verify WhatsApp broadcast uses get_current_admin in `api/routes/whatsapp.py`
3. Add `Depends(get_current_user)` to all `/api/ai/*` endpoints in `api/routes/ai_routes.py`
4. Fix Float → Numeric(12,2) on all money fields across ALL model files
5. Add CAPTCHA to `/api/auth/register` (Cloudflare Turnstile preferred — free tier)
6. Add account lockout: 5 failed attempts → 15-minute block tracked in Redis
7. Add database SSL enforcement: `?ssl=require` to DATABASE_URL in production
8. Add Redis password configuration in `docker-compose.yml` and `.env.example`
9. Write integration tests for: auth flow (register → login → refresh → logout) and payment flow (initiate → callback → verification auto-trigger)
10. Fix `run_in_executor` for AI engine calls in `services/ai_service.py`, `valuation_service.py`, `whatsapp_service.py`

### PHASE 2: REVENUE ENGINE (Days 4-10)
**Goal: First paying customers, MRR > KES 200K**

11. **Complete paid verification report flow**:
    - Create `services/report_service.py` — PDF generation with reportlab
    - Create `api/routes/reports.py` — GET `/api/reports/verification/{id}/pdf`
    - Branded PDF with: VESTRA header, property details, trust score (0-100 gauge), fraud flags, price analysis, ownership confidence, AI summary, QR code linking to live report
12. **Complete agent subscription gating** in `services/subscription_service.py`:
    - Free: 5 listings, no featured, basic search
    - Basic (KES 1,500/mo): 20 listings, basic analytics, verification at 20% discount
    - Pro (KES 5,000/mo): 50 listings, featured listings, advanced analytics, WhatsApp tools, priority support
    - Premium (KES 15,000/mo): unlimited listings, priority support, API access, team accounts (up to 3), dedicated account manager
    - Enforce limits in `property_service.py` (check subscription before allowing create/publish)
13. **Complete listing fee enforcement**:
    - Track listing count per user per month
    - First 3 free for unsubscribed users, then KES 300/listing
    - Check in `POST /api/properties/`
14. **Complete featured listings**:
    - Add `is_featured` and `featured_expires_at` to Property model
    - Payment → set `is_featured=True` + expires in 30 days
    - Sort featured listings higher in search results
15. **Create frontend subscription page** at `app/subscription/page.tsx`:
    - Plan comparison table (Free / Basic / Pro / Premium)
    - Feature checkmarks for each tier
    - "Upgrade" button → M-Pesa payment flow
    - Current plan highlighted

### PHASE 3: KYC + TRUST INFRASTRUCTURE (Days 5-8)
**Goal: Identity verification backbone that enables trust scoring**

16. **Complete KYC service** in `services/kyc_service.py`:
    - `submit_kyc()` — validate ID uploads, create KYCVerification record
    - `get_kyc_status()` — return current status + reviewer notes
    - `admin_review_kyc()` — approve/reject with rejection reason
    - `get_pending_kyc()` — for admin queue
17. **Complete KYC routes** in `api/routes/kyc.py`:
    - POST `/api/kyc/submit` — accepts multipart: id_front, id_back, selfie
    - GET `/api/kyc/status` — returns KYC status for current user
    - PUT `/api/kyc/admin/review/{id}` — admin approve/reject
    - GET `/api/kyc/admin/pending` — admin queue
18. **Create frontend KYC components**:
    - `components/kyc/KYCForm.tsx` — ID upload with drag-and-drop, camera capture for selfie
    - `components/kyc/KYCStatus.tsx` — verification status with badge
19. **Create admin KYC review page** at `app/admin/kyc/page.tsx`
20. **Wire KYC status into user profile** — is_kyc_verified field, badge on profile

### PHASE 4: MESSAGING + NOTIFICATIONS (Days 7-10)
**Goal: Users can communicate on-platform, get real-time alerts**

21. **Complete messaging service** in `services/messaging_service.py`:
    - `send_message()` — create message record, optionally trigger notification
    - `get_conversations()` — list unique sender/receiver pairs with last message
    - `get_conversation()` — paginated messages between two users
    - `mark_as_read()` — set is_read=True
    - `get_unread_count()` — count unread messages for user
22. **Complete messaging routes** in `api/routes/messages.py`:
    - POST `/api/messages` — send message
    - GET `/api/messages` — list conversations
    - GET `/api/messages/{id}` — get conversation with messages
    - PUT `/api/messages/{id}/read` — mark as read
    - GET `/api/messages/unread-count` — unread badge count
23. **Complete notification service** in `services/notification_service.py`:
    - `create_notification()` — create DB record + optionally send email/WhatsApp
    - `get_notifications()` — paginated list
    - `mark_read()` / `mark_all_read()`
    - `get_unread_count()`
24. **Complete notification routes** in `api/routes/notifications.py`
25. **Create frontend messaging page** at `app/messages/page.tsx`:
    - Left panel: conversation list with last message preview
    - Right panel: chat view with message bubbles
    - Compose button → new message modal
26. **Add notification badge to navbar** — unread count with red dot
27. **Wire message notifications** — when property inquiry sent, notify agent via email + in-app

### PHASE 5: RENT COLLECTION (Days 11-17)
**Goal: Kenya's #1 automated rent collection platform — 2% per transaction**

28. **Complete rental service** in `services/rental_service.py`:
    - `collect_rent()` — initiate M-Pesa STK Push for rent amount
    - `schedule_rent()` — set up recurring monthly collection
    - `get_landlord_units()` — all units with tenant and payment status
    - `get_tenant_payments()` — payment history for a tenant
    - `get_collection_stats()` — collection rate, arrears, monthly totals
    - `generate_receipt()` — PDF rent receipt
29. **Complete rental routes** in `api/routes/rentals.py`:
    - POST `/api/rentals/collect/{unit_id}` — trigger one-time rent collection
    - POST `/api/rentals/schedule/{lease_id}` — set monthly auto-collection
    - DELETE `/api/rentals/schedule/{lease_id}` — cancel auto-collection
    - GET `/api/rentals/units` — landlord's units list
    - GET `/api/rentals/dashboard` — collection stats + charts
    - GET `/api/rentals/unit/{id}/payments` — payment history for a unit
    - GET `/api/rentals/unit/{id}/receipt/{payment_id}` — download receipt PDF
30. **Create frontend landlord dashboard** at `app/dashboard/landlord/page.tsx`:
    - Overview cards: total units, occupied, collection rate, arrears
    - Units table: unit name, tenant, rent amount, last paid, status
    - "Collect Rent" button per unit → M-Pesa STK Push
    - "Auto-Collect" toggle per lease
    - Chart: monthly collection vs arrears
31. **Create rent receipt PDF generation** in `services/receipt_service.py`

### PHASE 6: ENTERPRISE API (Days 18-24)
**Goal: Banks, SACCOs, insurers pay KES 25K-150K/month for access**

32. **Complete API key service** in `services/api_key_service.py`:
    - `create_api_key()` — generate random key, store SHA-256 hash, return key once
    - `validate_api_key()` — hash submitted key, check against DB
    - `get_user_keys()` — list keys with prefixes
    - `revoke_api_key()` — set is_active=False
    - `record_usage()` — track API call per key
33. **Complete API key routes** in `api/routes/enterprise.py`:
    - POST `/api/enterprise/keys` — create key
    - GET `/api/enterprise/keys` — list keys
    - DELETE `/api/enterprise/keys/{id}` — revoke key
    - GET `/api/enterprise/usage` — usage analytics (calls per day, endpoints)
34. **Complete webhook system** in `services/webhook_service.py`:
    - `register_webhook()` — store URL + events to listen for
    - `trigger_webhook()` — POST event data to registered URLs with retry
    - Events to support: property.created, property.verified, payment.completed, verification.completed
35. **Create enterprise portal pages**:
    - `app/enterprise/page.tsx` — API documentation with examples
    - `app/enterprise/keys/page.tsx` — API key management UI
    - `app/enterprise/webhooks/page.tsx` — webhook configuration UI

### PHASE 7: ADMIN CONTROL PANEL + ANALYTICS (Days 22-28)
**Goal: Full operational control — review queues, moderation, system management**

36. **Enrich admin dashboard** (`app/admin/page.tsx`):
    - Currently shows stats — add action panels
    - Quick action cards: "Review Verifications (N pending)", "Review KYC (N pending)", "Active Disputes (N)"
    - Recent activity feed
37. **Create admin verification queue** at `app/admin/verifications/page.tsx`:
    - Table: property, owner, trust score, fraud score, AI recommendation, date
    - Click to expand: AI summary, document flags, price analysis
    - Actions: Approve / Flag / Reject with notes
    - Filter: status, date range, trust score range
38. **Create admin dispute management** at `app/admin/disputes/page.tsx`:
    - Table: reporter, subject, category, status, date
    - Click to view: description, evidence, chat history
    - Actions: Update status, add resolution notes, assign to admin
39. **Create admin fraud investigation** at `app/admin/fraud/page.tsx`:
    - Table: reported phone/email/title deed, reporter, description, status
    - Cross-reference: search properties by phone/email
    - Actions: Confirm fraudulent, dismiss, request more info
40. **Create data collection pipeline** in `services/analytics_service.py`:
    - Track every search query → results clicked → inquiry sent (full funnel data)
    - Track property views → time on page → saved → shared
    - Track verification predictions vs. human reviewer decisions
    - Track price changes over time per city/property type
    - Track tenant payment history

---

## QUALITY REQUIREMENTS (Run Before Marking Task Complete)

1. Run `python -c "import compileall; compileall.compile_dir('vestra/backend/app')"` — zero errors
2. Run `npx tsc --noEmit` from `vestra/frontend-build` — zero type errors
3. All new API endpoints return proper status codes: 200 (success), 201 (created), 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found), 422 (validation error), 429 (rate limited), 500 (internal error)
4. All new frontend pages handle: loading state (spinner), empty state (helpful message + CTA), error state (error message + retry), success state (full content)
5. No `console.log` in production code
6. No `any` TypeScript type — use proper interfaces from `@/types`
7. All money fields use `Numeric(12,2)` — never `Float` for currency
8. All new routes registered in `vestra/backend/app/api/__init__.py`
9. All new models exported in `vestra/backend/app/models/__init__.py`
10. All new frontend API methods added to `vestra/frontend-build/lib/api.ts`
11. All new TypeScript types added to `vestra/frontend-build/types/index.ts`
12. No hardcoded URLs or secrets — use `settings` config (backend) or env vars (frontend)
13. Every `except:` block logs the error and returns a structured JSON response
14. Every async AI engine call uses `run_in_executor` — not a single blocking call on the event loop
15. Every M-Pesa callback has replay protection (check `checkout_request_id` against processed set)

---

## REVENUE MODEL (For Context When Building)

| Stream | Price | Billing | Monthly at Month 12 |
|--------|-------|---------|---------------------|
| Verification Report | KES 500 | Per report | ~KES 3.25M |
| Agent Basic | KES 1,500 | Monthly | ~KES 1.9M |
| Agent Pro | KES 5,000 | Monthly | ~KES 2.5M |
| Agent Premium | KES 15,000 | Monthly | ~KES 2.25M |
| Listing Fee | KES 300 | Per listing | ~KES 720K |
| Featured Listing | KES 1,000 | Per 30 days | ~KES 500K |
| Rent Collection (2%) | 2% | Per transaction | ~KES 260K (early) |
| Enterprise API | KES 25K-150K | Monthly | ~KES 500K-2M |
| **Total Potential** | | | **KES 12-16M/month** |

---

## START HERE

Phase 1, Task 1: Open `vestra/backend/app/api/routes/payments.py` and verify the M-Pesa callback has Safaricom IP whitelist active for production. Read all the files listed in "FILES YOU MUST READ FIRST" before writing any code. Then proceed through the 7 phases in order.
