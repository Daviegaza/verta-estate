# VESTRA Strategic Analysis — June 2026
## Founder-Level & Engineer-Level Plan for Africa's Best Real Estate Platform

---

## EXECUTIVE SUMMARY

VESTRA is a **solid foundation** — well-architected for an MVP, with genuinely impressive infrastructure (JWT IP-binding, Redis rate limiting, Prometheus metrics, structured logging, comprehensive security headers, PWA support). The backend has 10+ models, 15 services, and 10 route modules covering the core real estate workflows. The frontend is clean Next.js 16 with React 19, Zustand state management, and good component architecture.

**However, the system is not production-ready and is not revenue-ready.** There are critical security vulnerabilities, missing revenue infrastructure, zero tests, a rule-based "AI" engine that needs real ML to be defensible, and significant gaps in the business logic layer.

**The biggest risk:** VESTRA could launch and get traction, then lose user trust from a single security incident (the M-Pesa callback is unauthenticated — anyone can fake payments) or regulatory issue.

**The biggest opportunity:** Kenya's real estate market is massive (~$12B+ annually) and deeply broken. No existing platform combines verified listings, AI trust scoring, M-Pesa payments, rental management, and agent tools. First-mover advantage is real.

**This report gives you:**
1. What's broken — prioritized by severity
2. What to build — in exact 30/60/90-day order
3. How to make money — 12-month revenue model with KES pricing
4. Database/backend/frontend changes — exact files and schemas
5. Production checklist — security, legal, operations
6. Go-to-market plan for Kenya

---

## 1. BIGGEST OPPORTUNITIES (Ranked by Revenue × Feasibility)

| # | Opportunity | Monthly Revenue Potential | Difficulty | Time to Revenue |
|---|------------|--------------------------|------------|-----------------|
| 1 | **Paid Verification Reports** — AI-powered property trust reports | KES 2-5M | Low | 2-4 weeks |
| 2 | **Agent Subscriptions** — Tiered SaaS for agents | KES 1-3M | Medium | 4-6 weeks |
| 3 | **Listing Fees** — Pay-per-listing for sellers/landlords | KES 500K-2M | Low | 2-3 weeks |
| 4 | **Rent Collection** — M-Pesa automated rent + 2-3% fee | KES 1-5M | Medium | 6-8 weeks |
| 5 | **Featured Listings** — Visibility boosts for agents/sellers | KES 200K-1M | Low | 1-2 weeks |
| 6 | **Tenant Screening Reports** — Background/credit checks | KES 500K-1.5M | Medium | 4-6 weeks |
| 7 | **Enterprise API** — Banks, SACCOs, insurers access verified data | KES 500K-5M | High | 3-6 months |
| 8 | **Title Deed Verification** — Land registry cross-check service | KES 300K-1M | Medium | 4-8 weeks |
| 9 | **WhatsApp Property Assistant** — Inbound lead gen + premium listing distribution | KES 200K-500K | Medium | 3-4 weeks |
| 10 | **Escrow/Deposit Protection** — Secure transaction holding | KES 500K-3M | High | 3-4 months |

**Immediate focus: #1, #2, #3, #5 — these can be generating revenue within 30 days.**

---

## 2. BIGGEST RISKS (Ranked by Impact × Likelihood)

### Critical (Fix Before Any Launch)

| # | Risk | Impact | Fix Effort |
|---|------|--------|------------|
| 1 | **M-Pesa callback has ZERO authentication** — any HTTP client can POST to `/api/payments/mpesa/callback` and trigger payment completion, subscription activation, verification | Catastrophic: fake payments, stolen subscriptions, trust destroyed | 2 hours |
| 2 | **WhatsApp broadcast uses wrong auth** — `get_current_user` instead of `get_current_admin`, any registered user can broadcast to unlimited recipients | High: spam, WhatsApp ban, reputational damage | 5 minutes |
| 3 | **AI endpoints unauthenticated** — `/api/ai/*` endpoints consume compute with no auth, rate limiting, or cost controls | Medium: resource drain, cost overrun | 30 minutes |
| 4 | **`next.config.ts` allows `hostname: '**'`** for images — SSRF/open-proxy risk if user-provided URLs are processed | Medium: potential data exfiltration | 5 minutes |
| 5 | **Docker Compose has hardcoded production secrets** — `SECRET_KEY`, `POSTGRES_PASSWORD` defaults | High if deployed as-is | 10 minutes |
| 6 | **No database SSL or Redis auth** — plaintext connections, no encryption at rest | Medium: data exposure risk | 1-2 hours |

### High (Fix Within 2 Weeks)

| # | Risk | Impact |
|---|------|--------|
| 7 | **Zero automated tests** — no pytest, no Jest, no integration tests. Any change could break payment flows | Revenue loss, bugs in production |
| 8 | **`upgrade_subscription` has async bug** — missing `await` on `_get_role_from_sub()`, returns coroutine instead of string | Subscription upgrades silently break |
| 9 | **`count_users` defined twice** — second definition overwrites first, breaking role-filtered counting | Admin stats are wrong |
| 10 | **AI engine blocks event loop** — synchronous calls in async functions, no `run_in_executor` | Performance degradation under load |
| 11 | **No M-Pesa access token caching** — new OAuth token fetched for every request | Unnecessary API calls, slower payments |
| 12 | **Property price uses `Float`** not `Numeric(12,2)` — floating point rounding errors on money | Financial inaccuracy |
| 13 | **User phone nullable but Tenant phone NOT NULL** — no link from Tenant to User | Duplicate data, identity fragmentation |
| 14 | **Frontend `filters` object causes re-render loop** in Market page | Performance bug |
| 15 | **Pagination hard-limited to 5 pages** — `Math.min(5, pages)` | Users can't browse beyond page 5 |

### Medium (Fix Within 30 Days)

| # | Risk |
|---|------|
| 16 | No escrow/transaction model — no way to track deals from offer to completion |
| 17 | No notification system — users have no in-app alerts |
| 18 | No messaging/inquiry system — buyers can't contact sellers through the platform |
| 19 | No KYC model — verification is boolean flag, not a workflow |
| 20 | No dispute/support ticket model |
| 21 | No soft-delete on properties — hard delete loses data forever |
| 22 | `__init__.py` doesn't export half the models |
| 23 | Email service uses `CORS_ORIGINS[0]` as base URL — fragile |
| 24 | Referral codes stored only in Redis (no DB fallback) |
| 25 | TitleChain has no `relationship()` to Property |
| 26 | No `.dockerignore` — bloated Docker build context |
| 27 | Render deployment config uses static export (incompatible with Next.js App Router) |
| 28 | No account lockout after failed login attempts |
| 29 | SMS OTP / 2FA completely absent |
| 30 | Cache failures silently swallowed — no observability |

---

## 3. SECURITY AUDIT — FIXES REQUIRED BEFORE PRODUCTION

### Immediate (Today)

```python
# 1. FIX: M-Pesa callback authentication
# File: vestra/backend/app/api/routes/payments.py
# Add IP whitelist OR HMAC signature verification OR shared secret

# Current (BROKEN):
@router.post("/mpesa/callback")
async def mpesa_callback(callback_data: dict, db: AsyncSession = Depends(get_db)):
    # NO AUTHENTICATION AT ALL
    result = await handle_mpesa_callback(db, callback_data)
    ...

# Fix:
@router.post("/mpesa/callback")
async def mpesa_callback(
    request: Request,
    callback_data: dict,
    db: AsyncSession = Depends(get_db)
):
    # Verify Safaricom IP range: 196.201.214.200/29 or 196.201.214.208/28
    client_ip = request.client.host
    if not is_safaricom_ip(client_ip):
        logger.warning(f"MPesa callback from non-Safaricom IP: {client_ip}")
        return {"ResultCode": 0, "ResultDesc": "Accepted"}  # Don't reveal rejection
    
    # Add HMAC signature verification if Safaricom provides it
    # Add replay protection (check if checkout_request_id already processed)
    ...
```

```python
# 2. FIX: WhatsApp broadcast authorization
# File: vestra/backend/app/api/routes/whatsapp.py
# Change: get_current_user → get_current_admin

# Current:
@router.post("/broadcast")
async def broadcast_message(
    phones: list[str],
    message: str,
    current_user = Depends(get_current_user),  # BUG: should be admin
):
    ...

# Fix:
@router.post("/broadcast")
async def broadcast_message(
    phones: list[str],
    message: str,
    current_user = Depends(get_current_admin),  # CORRECT
):
    ...
```

### This Week

3. **Add auth to AI endpoints** — wrap with `get_current_user` (free tier has limited calls, paid tiers have more)
4. **Fix `next.config.ts` images** — remove `hostname: '**'`, allow only known domains
5. **Add database SSL** — add `?ssl=require` to DATABASE_URL
6. **Add Redis password** — configure `requirepass` in redis.conf and update REDIS_URL
7. **Add rate limiting on login** — account lockout after 5 failed attempts in 15 minutes
8. **Add CAPTCHA to registration** — hCaptcha or Cloudflare Turnstile (free)

### This Month

9. **Implement proper M-Pesa webhook verification** — Safaricom's actual HMAC signature if available, or IP whitelist + shared secret
10. **Move JWT to RS256** — asymmetric keys for multi-service verification
11. **Add SMS OTP for sensitive operations** — payments, password changes, phone changes
12. **Implement CSRF protection** — the config flag exists but middleware doesn't
13. **Run full OWASP ZAP scan** before production launch
14. **Engage a Kenyan data protection lawyer** — review against Data Protection Act 2019

---

## 4. REVENUE MODEL — 12-Month Projections

### Pricing (KES)

| Product | Tier | Price | Billing |
|---------|------|-------|---------|
| **Verification Report** | One-time | KES 500 | Per report |
| **Agent Basic** | Monthly | KES 1,500 | Monthly |
| **Agent Pro** | Monthly | KES 5,000 | Monthly |
| **Agent Premium** | Monthly | KES 15,000 | Monthly |
| **Landlord Basic** (≤2 units) | Monthly | KES 1,000 | Monthly |
| **Landlord Pro** (≤10 units) | Monthly | KES 3,500 | Monthly |
| **Landlord Premium** (≤100 units) | Monthly | KES 10,000 | Monthly |
| **Featured Listing** | One-time | KES 1,000 | Per listing (30 days) |
| **Seller Listing** | One-time | KES 300 | Per listing (free first) |
| **Tenant Screening** | One-time | KES 400 | Per report |
| **Rent Collection** | Transaction | 2% | Per transaction (cap KES 500) |
| **Enterprise API** | Monthly | KES 25,000-150,000 | Tiered by volume |

### 12-Month Revenue Projections

#### Conservative Case (Slow Organic Growth)

| Month | Users | Listings | Verifications | Agent Subs | Landlord Subs | Rent TXN (KES) | MRR (KES) |
|-------|-------|----------|---------------|------------|---------------|----------------|-----------|
| 1 | 200 | 50 | 20 | 5 | 2 | 0 | 21,500 |
| 2 | 500 | 120 | 50 | 12 | 5 | 0 | 53,500 |
| 3 | 1,200 | 300 | 120 | 25 | 10 | 50,000 | 129,000 |
| 4 | 2,500 | 600 | 250 | 50 | 20 | 150,000 | 305,000 |
| 5 | 4,500 | 1,200 | 500 | 90 | 40 | 400,000 | 623,000 |
| 6 | 8,000 | 2,000 | 800 | 150 | 70 | 800,000 | 1,091,000 |
| 7 | 13,000 | 3,500 | 1,200 | 230 | 120 | 1,500,000 | 1,940,000 |
| 8 | 20,000 | 5,500 | 1,800 | 350 | 180 | 2,500,000 | 3,080,000 |
| 9 | 30,000 | 8,000 | 2,500 | 500 | 280 | 4,000,000 | 4,780,000 |
| 10 | 42,000 | 12,000 | 3,500 | 700 | 400 | 6,000,000 | 6,960,000 |
| 11 | 58,000 | 17,000 | 4,800 | 950 | 550 | 9,000,000 | 10,055,000 |
| 12 | 80,000 | 24,000 | 6,500 | 1,300 | 750 | 13,000,000 | 14,620,000 |

**Year 1 Revenue: ~KES 43M (~$320K USD)**

#### Realistic Case (Active Agent Recruitment + WhatsApp Growth)

| Month | MRR (KES) | Notes |
|-------|-----------|-------|
| 1 | 65,000 | Initial agent onboarding push |
| 2 | 180,000 | WhatsApp acquisition kicks in |
| 3 | 420,000 | First enterprise client |
| 4 | 850,000 | Rent collection launches |
| 5 | 1,500,000 | Referral program compounds |
| 6 | 2,400,000 | Nairobi market established |
| 7 | 3,600,000 | Mombasa/Kisumu expansion |
| 8 | 5,200,000 | Second enterprise client |
| 9 | 7,000,000 | Bank partnership |
| 10 | 9,500,000 | Insurance partnership |
| 11 | 12,500,000 | Multi-city traction |
| 12 | 16,000,000 | |

**Year 1 Revenue: ~KES 58M (~$430K USD)**

#### Aggressive Case (VC-backed growth with field team)

| Month | MRR (KES) | Notes |
|-------|-----------|-------|
| 1 | 120,000 | Paid launch campaign |
| 2 | 400,000 | Field agents in 5 cities |
| 3 | 900,000 | 3 enterprise clients |
| 4 | 1,800,000 | Rent collection at scale |
| 5 | 3,200,000 | Radio/TV advertising |
| 6 | 5,500,000 | Government partnership |
| 7 | 8,000,000 | 10 enterprise clients |
| 8 | 12,000,000 | Kenya-wide coverage |
| 9 | 16,000,000 | Tanzania expansion prep |
| 10 | 22,000,000 | Bank API revenue |
| 11 | 28,000,000 | Insurance revenue |
| 12 | 35,000,000 | |

**Year 1 Revenue: ~KES 132M (~$980K USD)**

### Cost Structure (Monthly at Month 12)

| Item | Conservative | Realistic | Aggressive |
|------|-------------|-----------|------------|
| Cloud hosting (Fly.io/Render) | KES 40,000 | KES 80,000 | KES 200,000 |
| Database (managed PostgreSQL) | KES 25,000 | KES 50,000 | KES 120,000 |
| Redis | KES 8,000 | KES 15,000 | KES 35,000 |
| M-Pesa API fees | KES 45,000 | KES 90,000 | KES 220,000 |
| WhatsApp API | KES 15,000 | KES 35,000 | KES 80,000 |
| Email (SendGrid/Mailgun) | KES 3,000 | KES 8,000 | KES 20,000 |
| Domain + SSL | KES 3,000 | KES 3,000 | KES 5,000 |
| Monitoring (Sentry, etc.) | KES 12,000 | KES 25,000 | KES 50,000 |
| **Infrastructure Total** | **KES 151,000** | **KES 306,000** | **KES 730,000** |
| | | | |
| Team (you + 2 engineers) | KES 450,000 | KES 600,000 | KES 900,000 |
| Customer support (1-2 people) | KES 60,000 | KES 120,000 | KES 240,000 |
| Field agents (commission) | KES 50,000 | KES 150,000 | KES 400,000 |
| Marketing | KES 50,000 | KES 200,000 | KES 1,000,000 |
| Legal/compliance | KES 30,000 | KES 60,000 | KES 150,000 |
| **Operations Total** | **KES 640,000** | **KES 1,130,000** | **KES 2,690,000** |
| | | | |
| **Total Monthly Costs** | **KES 791,000** | **KES 1,436,000** | **KES 3,420,000** |
| **MRR (Month 12)** | **KES 14,620,000** | **KES 16,000,000** | **KES 35,000,000** |
| **Gross Margin** | **94.6%** | **91.0%** | **90.2%** |

---

## 5. DATABASE DESIGN — NEW MODELS NEEDED

### Priority 1: Revenue-Enabling Models (Week 1-2)

```python
# KYC Verification
class KYCVerification(Base):
    __tablename__ = "kyc_verifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(KYCStatus), default=KYCStatus.pending)  # pending/reviewing/approved/rejected
    id_type = Column(String(50))  # national_id, passport, alien_id
    id_number = Column(String(50))
    id_front_url = Column(String(1000))
    id_back_url = Column(String(1000))
    selfie_url = Column(String(1000))
    ocr_data = Column(JSON, default=dict)  # Extracted text from ID
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Annual re-verification
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Favorites / Saved Properties
class SavedProperty(Base):
    __tablename__ = "saved_properties"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "property_id"),)

# Saved Searches
class SavedSearch(Base):
    __tablename__ = "saved_searches"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    filters = Column(JSON, default=dict)  # Stored search criteria
    notify_email = Column(Boolean, default=True)
    notify_whatsapp = Column(Boolean, default=False)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Notifications
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # new_listing, price_drop, payment_received, rent_due, etc.
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    data = Column(JSON, default=dict)  # Link data (property_id, payment_id, etc.)
    is_read = Column(Boolean, default=False)
    channel = Column(String(20), default="in_app")  # in_app, email, whatsapp, sms
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### Priority 2: Platform Integrity Models (Week 3-4)

```python
# Messages / Inquiries
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Reviews/Ratings
class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Agent/landlord being reviewed
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    is_verified_transaction = Column(Boolean, default=False)  # Only if actual deal happened
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("reviewer_id", "subject_id", "property_id"),)

# Escrow / Transactions
class EscrowTransaction(Base):
    __tablename__ = "escrow_transactions"
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount_kes = Column(Numeric(12, 2), nullable=False)
    deposit_amount_kes = Column(Numeric(12, 2), nullable=True)  # 10% deposit
    status = Column(String(30), default="initiated")  # initiated/deposit_paid/balance_paid/completed/cancelled/refunded
    payment_reference = Column(String(255), nullable=True)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Disputes
class Dispute(Base):
    __tablename__ = "disputes"
    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    subject_type = Column(String(50))  # property, agent, landlord, tenant, payment
    subject_id = Column(Integer, nullable=True)
    category = Column(String(50))  # fraud, misrepresentation, payment, harassment, other
    description = Column(Text, nullable=False)
    evidence_urls = Column(JSON, default=list)
    status = Column(String(30), default="open")  # open/investigating/resolved/closed
    resolution = Column(Text, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Fraud Reports / Blacklist
class FraudReport(Base):
    __tablename__ = "fraud_reports"
    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reported_phone = Column(String(20), nullable=True, index=True)
    reported_email = Column(String(255), nullable=True, index=True)
    reported_title_deed = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=False)
    evidence_urls = Column(JSON, default=list)
    status = Column(String(30), default="pending")  # pending/investigating/confirmed/false_report
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# API Keys (Enterprise)
class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    key_hash = Column(String(128), nullable=False)  # SHA-256 hash of the key
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for display
    scopes = Column(JSON, default=list)  # ["read:properties", "read:verifications", ...]
    rate_limit_per_min = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### Priority 3: Operations Models (Month 2)

```python
# Rent Receipts
class RentReceipt(Base):
    __tablename__ = "rent_receipts"
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("rent_payments.id"), nullable=False)
    receipt_number = Column(String(50), unique=True, nullable=False)
    pdf_url = Column(String(1000), nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

# Property Inspection Reports
class InspectionReport(Base):
    __tablename__ = "inspection_reports"
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("rental_units.id"), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(30))  # move_in, move_out, periodic
    report_data = Column(JSON, default=dict)
    images = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Coupons / Promo Codes
class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_type = Column(String(20))  # percentage, fixed
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_purchase_kes = Column(Numeric(10, 2), default=0)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    applies_to = Column(JSON, default=list)  # ["verification", "subscription", "listing"]
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Payouts (for agents, landlords, referrers)
class Payout(Base):
    __tablename__ = "payouts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_kes = Column(Numeric(12, 2), nullable=False)
    type = Column(String(30))  # referral_reward, commission, rent_collection_fee_rebate
    status = Column(String(30), default="pending")  # pending/processing/completed/failed
    mpesa_phone = Column(String(20), nullable=False)
    mpesa_receipt = Column(String(100), nullable=True)
    reference = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## 6. BACKEND IMPLEMENTATION PLAN — NEW MODULES

### New Services Needed

```
vestra/backend/app/services/
├── kyc_service.py           # ID verification, OCR result processing
├── notification_service.py  # Multi-channel notifications (in-app, email, WhatsApp, SMS)
├── messaging_service.py     # Buyer-seller-agent messaging
├── escrow_service.py        # Secure transaction holding and release
├── review_service.py        # Ratings and reviews
├── dispute_service.py       # Dispute management
├── fraud_service.py         # Fraud reporting and blacklist
├── receipt_service.py       # PDF receipt generation
├── report_service.py        # PDF verification report generation
├── coupon_service.py        # Discount/promo code management
├── payout_service.py        # M-Pesa B2C disbursements
├── api_key_service.py       # Enterprise API key management
├── webhook_service.py       # Outbound webhooks for enterprise clients
└── search_alert_service.py  # Saved search notifications
```

### New Route Modules Needed

```
vestra/backend/app/api/routes/
├── kyc.py              # POST /kyc/submit, GET /kyc/status, PUT /kyc/admin/review
├── messages.py         # POST /messages, GET /messages, GET /messages/{id}, PUT /messages/{id}/read
├── reviews.py          # POST /reviews, GET /reviews/user/{id}, GET /reviews/property/{id}
├── escrow.py           # POST /escrow/initiate, POST /escrow/deposit, POST /escrow/complete
├── disputes.py         # POST /disputes, GET /disputes, PUT /disputes/{id}
├── fraud.py            # POST /fraud/report, GET /fraud/check?phone=...&email=...
├── reports.py          # GET /reports/verification/{id}/pdf, GET /reports/rent-receipt/{id}/pdf
├── notifications.py    # GET /notifications, PUT /notifications/{id}/read, PUT /notifications/read-all
├── enterprise.py       # POST /enterprise/keys, GET /enterprise/keys, DELETE /enterprise/keys/{id}
├── favorites.py        # POST /favorites, GET /favorites, DELETE /favorites/{property_id}
├── saved_searches.py   # POST /searches, GET /searches, DELETE /searches/{id}
└── webhooks.py         # POST /webhooks/register, GET /webhooks, DELETE /webhooks/{id}
```

### Services to Refactor (Critical Fixes)

| Service | What to Fix | Priority |
|---------|------------|----------|
| `mpesa_service.py` | Cache access token (1hr TTL), connection pooling, retry logic, B2C support | P0 |
| `payment_service.py` | Move prices to config/DB, add idempotency, add refund support, add receipt generation | P0 |
| `ai_service.py` | Wrap in `run_in_executor`, add rate limiting, add error handling, add caching | P0 |
| `subscription_service.py` | Fix `await` bug, add proration, add invoice generation, add dunning management | P0 |
| `email_service.py` | Queue-based sending (Redis/Celery), proper base URL config, Swahili templates | P1 |
| `verification_service.py` | Fix `agent_profile` null check, fix cache dict vs ORM issue, add PDF report generation | P1 |
| `referral_engine.py` | DB-backed codes (not Redis-only), add payout support, add fraud detection | P1 |
| `whatsapp_service.py` | Session management for multi-step flows, user account linking, opt-out handling | P1 |
| `search_service.py` | Add trigram fuzzy search, geospatial search, search analytics | P2 |
| `rental_service.py` | Enforce subscription limits, fix rent bill date bug, add receipt generation | P2 |
| `property_service.py` | Soft delete, image management, favorites integration | P2 |
| `title_chain.py` | Add Property relationship, pagination, Merkle proofs | P3 |

---

## 7. FRONTEND IMPLEMENTATION PLAN — NEW PAGES & COMPONENTS

### New Pages Needed

```
vestra/frontend-build/app/
├── dashboard/                    # User dashboard (role-based)
│   └── page.tsx
├── dashboard/agent/              # Agent dashboard
│   ├── page.tsx                  # Overview: listings, leads, earnings
│   ├── listings/page.tsx         # Manage listings
│   ├── leads/page.tsx            # Inquiries and messages
│   └── earnings/page.tsx         # Revenue and payouts
├── dashboard/landlord/           # Landlord dashboard
│   ├── page.tsx                  # Overview: units, occupancy, collection rate
│   ├── units/page.tsx            # Unit management
│   ├── tenants/page.tsx          # Tenant management
│   ├── rent/page.tsx             # Rent collection dashboard
│   ├── maintenance/page.tsx      # Maintenance tracking
│   └── reports/page.tsx          # Rental reports
├── dashboard/buyer/              # Buyer dashboard
│   ├── page.tsx                  # Saved properties, searches, comparisons
│   ├── favorites/page.tsx
│   └── searches/page.tsx
├── dashboard/admin/              # Admin dashboard (expand existing)
│   ├── page.tsx                  # Already exists, needs enrichment
│   ├── verifications/page.tsx    # Verification review queue
│   ├── kyc/page.tsx              # KYC review queue
│   ├── disputes/page.tsx         # Dispute management
│   ├── fraud/page.tsx            # Fraud investigation
│   └── enterprise/page.tsx       # Enterprise API management
├── properties/                   # Property pages (expand)
│   ├── [id]/page.tsx             # Property detail (exists but needs enrichment)
│   ├── [id]/verify/page.tsx      # Verification flow
│   ├── [id]/report/page.tsx      # Trust report view
│   ├── compare/page.tsx          # Property comparison
│   └── new/page.tsx              # Create listing
├── verify/                       # Verification flow
│   ├── page.tsx                  # Start verification
│   └── [id]/page.tsx             # Verification status/results
├── agents/                       # Agent directory
│   ├── page.tsx                  # Browse agents
│   └── [id]/page.tsx             # Agent profile
├── subscriptions/                # Subscription management
│   ├── page.tsx                  # Plans comparison
│   └── manage/page.tsx           # Manage subscription
├── messages/                     # Messaging inbox
│   ├── page.tsx                  # Inbox
│   └── [id]/page.tsx             # Conversation
├── wallet/                       # Payment wallet
│   ├── page.tsx                  # Payment history, balance
│   └── payouts/page.tsx          # Withdrawal management
├── settings/                     # User settings
│   ├── page.tsx                  # Profile
│   ├── security/page.tsx         # Password, 2FA
│   ├── notifications/page.tsx    # Notification preferences
│   └── kyc/page.tsx              # KYC verification
└── enterprise/                   # Enterprise portal
    ├── page.tsx                  # API documentation
    └── keys/page.tsx             # API key management
```

### New Components Needed

```
vestra/frontend-build/components/
├── property/
│   ├── PropertyCompare.tsx       # Side-by-side property comparison
│   ├── PropertyMap.tsx           # Map view with markers (Leaflet/Mapbox)
│   ├── PropertyGallery.tsx       # Image gallery with zoom
│   ├── PropertyInquiry.tsx       # Contact seller form
│   └── PropertyShare.tsx         # Share via WhatsApp, social
├── verify/
│   ├── VerificationFlow.tsx      # Multi-step verification wizard
│   ├── DocumentUploader.tsx      # Drag-and-drop document upload
│   ├── OCRPreview.tsx            # OCR result review
│   ├── TrustReport.tsx           # Full trust report view
│   └── ReportDownload.tsx        # PDF download button
├── payment/
│   ├── MpesaPayment.tsx          # M-Pesa payment flow
│   ├── PaymentStatus.tsx         # Real-time payment status
│   ├── SubscriptionCard.tsx      # Plan selection card
│   └── WalletBalance.tsx         # Balance display
├── rental/
│   ├── RentDashboard.tsx         # Rent collection overview
│   ├── RentBillCard.tsx          # Individual rent bill
│   ├── TenantCard.tsx            # Tenant summary
│   ├── LeaseTimeline.tsx         # Lease duration visualization
│   └── MaintenanceTracker.tsx    # Maintenance request status
├── messaging/
│   ├── ConversationList.tsx      # Message thread list
│   ├── ChatBubble.tsx            # Individual message
│   └── ComposeMessage.tsx        # New message form
├── search/
│   ├── AISearchBar.tsx           # Natural language search
│   ├── FilterPanel.tsx           # Advanced filters
│   ├── SavedSearchCard.tsx       # Saved search with alerts
│   └── MapSearch.tsx             # Map-based property search
├── kyc/
│   ├── KYCForm.tsx               # ID upload + selfie
│   ├── KYCStatus.tsx             # Verification status
│   └── OCRResultReview.tsx       # Review extracted data
├── enterprise/
│   ├── APIKeyManager.tsx         # Create/revoke API keys
│   ├── UsageChart.tsx            # API usage analytics
│   └── WebhookManager.tsx        # Webhook configuration
├── common/
│   ├── EmptyState.tsx            # Empty state with action
│   ├── ConfirmDialog.tsx         # Confirmation modal
│   ├── ShareButton.tsx           # WhatsApp/social share
│   ├── DateRangePicker.tsx       # Date range filter
│   ├── SearchableSelect.tsx      # Searchable dropdown
│   ├── DataTable.tsx             # Sortable/filterable table
│   ├── StatCard.tsx              # Already exists as StatCard in ui/card
│   └── PageHeader.tsx            # Consistent page header with breadcrumbs
└── whatsapp/
    ├── WhatsAppSimulator.tsx     # Preview WhatsApp messages
    └── TemplateManager.tsx       # Message template editor
```

---

## 8. AI STRATEGY — FROM RULES TO MACHINE LEARNING

### Current State

The existing "AI engine" (`ai/engine.py`, 1004 lines) is entirely rule-based:
- Fraud detection: keyword matching + price bands
- Trust scoring: inverse of fraud + bonuses
- Valuation: city × sqft lookup tables
- Search parsing: regex-based extraction
- Market intelligence: hardcoded per-city summaries

This is **good enough for MVP** but **not defensible**. Any competitor can replicate rule-based checks. Real defensibility comes from proprietary data and ML models.

### Phase 1: Data Collection Infrastructure (Weeks 1-4 — Start NOW)

**Every user action must be recorded from day one.** ML models are useless without training data.

```python
# Add to existing or new models:

# User behavior tracking
class UserEvent(Base):
    __tablename__ = "user_events"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # search, view, inquiry, favorite, share, report_view
    event_data = Column(JSON, default=dict)
    client_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Property price history (track price changes)
class PriceChange(Base):
    __tablename__ = "price_changes"
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    old_price = Column(Numeric(12, 2), nullable=False)
    new_price = Column(Numeric(12, 2), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Verification outcome tracking (for model evaluation)
class VerificationOutcome(Base):
    __tablename__ = "verification_outcomes"
    id = Column(Integer, primary_key=True)
    verification_id = Column(Integer, ForeignKey("verifications.id"), nullable=False)
    ai_prediction = Column(JSON, default=dict)  # What the AI predicted
    human_decision = Column(String(20), nullable=False)  # What the reviewer decided
    was_correct = Column(Boolean, nullable=True)  # Was AI right?
    ground_truth_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Data to collect from day one:**
1. Search queries → results clicked → inquiries sent → deals closed (full funnel)
2. Property views → time on page → shares → favorites
3. Price changes over time per city/property type
4. Verification predictions vs. human reviewer decisions
5. Fraud reports → investigation outcomes
6. Tenant payment history (for credit scoring)
7. Agent deal completion rates
8. User-reported issues with properties

### Phase 2: Enhanced Rules + Simple ML (Month 2-3)

1. **Price prediction model** — Train a simple XGBoost/LightGBM model on:
   - Historical listing prices × final sale prices
   - City, neighborhood, bedrooms, sqft, amenities, year built
   - Comparable recent sales
   - Replace hardcoded `city_prices` lookup table

2. **Fraud detection enhancement** — Add these signals to the existing rule engine:
   - Image similarity detection (duplicate images across listings = fake listing signal)
   - Text similarity (copied descriptions)
   - Account age + verification status
   - Phone number / email cross-reference with fraud reports
   - Listing velocity (too many listings too fast = suspicious)

3. **Search relevance** — Replace regex-based parsing with:
   - Embedding-based semantic search (sentence-transformers)
   - Learning to rank from click data
   - Personalized results based on user behavior

### Phase 3: Deep Learning Models (Month 4-6)

1. **Document forgery detection** — CNN model for title deed / ID verification
   - Train on genuine vs forged Kenyan documents
   - Detect: font inconsistencies, stamp irregularities, photo manipulation
   - Integration with government land registry APIs (when available)

2. **Property image analysis** — Computer vision for:
   - Room type classification (bedroom vs living room vs kitchen)
   - Condition assessment (new, good, needs renovation, poor)
   - Amenity detection (AC units, solar panels, parking, garden)
   - Fraud detection (stock photos, images from other listings)

3. **Tenant credit scoring** — ML model using:
   - Rent payment history (on-platform)
   - Employment stability
   - Previous landlord references
   - M-Pesa transaction patterns (with consent)

4. **Price optimization for sellers/landlords** — Recommend optimal listing price based on:
   - Comparable properties
   - Market demand signals (views, inquiries)
   - Time-on-market predictions
   - Seasonal adjustments

### Phase 4: Defensible AI Products (Month 6-12)

1. **Automated Valuation Model (AVM)** — Compete with bank valuations at 1/10th the cost
2. **Rental yield prediction** — Predict rental income for investors
3. **Market trend forecasting** — Predict price movements by neighborhood
4. **Fraud network detection** — Graph neural networks to identify fraud rings
5. **WhatsApp AI assistant** — Conversational property search in English + Swahili

### AI Architecture Recommendation

```
vestra/backend/app/
├── ai/
│   ├── __init__.py
│   ├── engine.py              # Keep: rule-based engine (fast, always available)
│   ├── models/                # NEW: ML model serving
│   │   ├── __init__.py
│   │   ├── price_predictor.py
│   │   ├── fraud_detector.py
│   │   ├── image_analyzer.py
│   │   ├── document_verifier.py
│   │   └── tenant_scorer.py
│   ├── training/              # NEW: Model training pipelines
│   │   ├── __init__.py
│   │   ├── data_pipeline.py
│   │   ├── train_price_model.py
│   │   └── evaluate_models.py
│   ├── embeddings/            # NEW: Semantic search
│   │   ├── __init__.py
│   │   └── property_embeddings.py
│   └── features/              # NEW: Feature engineering
│       ├── __init__.py
│       ├── property_features.py
│       └── user_features.py
```

**Deployment strategy:**
- Rule-based engine: Always on, runs in-process (current approach — keep it)
- ML models: Deployed as separate microservice OR loaded via ONNX Runtime in-process
- Training: Offline (run weekly/monthly), not in the API server
- Feature store: Use Redis for real-time features, PostgreSQL for historical

---

## 9. PRODUCT ROADMAP — 5 PHASES

### Phase 1: Production-Ready MVP (Now — Week 4)
**Goal: Secure, stable, revenue-capable launch in Nairobi**

| Task | Priority | Effort |
|------|----------|--------|
| Fix all critical security vulnerabilities (see Section 3) | P0 | 1-2 days |
| Add authentication to M-Pesa callback | P0 | 2 hours |
| Fix WhatsApp broadcast auth bug | P0 | 5 min |
| Fix `upgrade_subscription` await bug | P0 | 5 min |
| Fix `count_users` duplicate definition | P0 | 5 min |
| Fix `next.config.ts` image wildcard | P0 | 5 min |
| Add `run_in_executor` for AI calls | P1 | 2 hours |
| Add M-Pesa token caching | P1 | 1 hour |
| Fix currency fields: Float → Numeric(12,2) | P1 | 2 hours |
| Add database SSL + Redis auth | P1 | 2 hours |
| Fix `__init__.py` model exports | P1 | 30 min |
| Fix frontend `filters` re-render loop | P1 | 1 hour |
| Fix pagination: remove `Math.min(5, pages)` limit | P1 | 30 min |
| Add proper `.dockerignore` files | P1 | 30 min |
| Fix Render deployment config (standalone, not static) | P1 | 1 hour |
| Set up Sentry error tracking | P1 | 2 hours |
| Set up UptimeRobot / Better Uptime monitoring | P1 | 1 hour |
| Add rate limiting on AI endpoints | P1 | 1 hour |
| Add CAPTCHA on registration | P2 | 3 hours |
| Write integration tests for payment flow | P2 | 1 day |
| Write integration tests for auth flow | P2 | 1 day |
| Set up CI test job (pytest + Jest) | P2 | 4 hours |
| Add account lockout after failed logins | P2 | 2 hours |
| Fix email service base URL (don't use CORS_ORIGINS) | P2 | 1 hour |

### Phase 2: Revenue Engine (Week 5-8)
**Goal: First paying customers, MRR > KES 200K**

| Feature | Revenue Impact | Effort |
|---------|---------------|--------|
| **Paid verification reports** — Full flow with M-Pesa payment | KES 500/report | 1 week |
| **Agent subscription tiers** — Upgrade/downgrade, feature gating | KES 1,500-15,000/mo | 1 week |
| **Listing fees** — Pay-per-listing beyond free tier | KES 300/listing | 3 days |
| **Featured listings** — Boost visibility for premium listings | KES 1,000/listing | 3 days |
| **Agent dashboard** — Listings, leads, earnings, analytics | Retention driver | 1 week |
| **Landlord dashboard** — Units, tenants, rent, maintenance | Retention driver | 1 week |
| **KYC verification flow** — ID upload, OCR, review | Trust driver | 1 week |
| **In-app messaging** — Buyer-seller-agent communication | Engagement driver | 1 week |
| **Notifications system** — Email + in-app alerts | Engagement driver | 3 days |
| **Saved properties & searches** — Favorites + alerts | Engagement driver | 2 days |
| **PDF trust report generation** — Downloadable verification reports | Value-add for reports | 3 days |
| **WhatsApp listing distribution** — Share properties via WhatsApp | Acquisition driver | 2 days |
| **Referral program activation** — Fix existing code + launch | Growth driver | 3 days |

### Phase 3: Rent & Property Management (Week 9-12)
**Goal: Recurring revenue from rent collection, landlord tools**

| Feature | Revenue Impact | Effort |
|---------|---------------|--------|
| **Automated rent collection** — M-Pesa STK Push for monthly rent | 2% per transaction | 2 weeks |
| **Rent dashboard** — Payment tracking, arrears, receipts | Landlord retention | 1 week |
| **Lease management** — Digital lease creation + e-signatures | Landlord retention | 1 week |
| **Maintenance marketplace** — Connect landlords with contractors | Future monetization | 1 week |
| **Tenant screening reports** — Background + payment history check | KES 400/report | 1 week |
| **Rent receipts** — Auto-generated PDF receipts | Value-add | 3 days |
| **Tenant portal** — View bills, pay rent, request maintenance | Tenant retention | 1 week |
| **WhatsApp rent reminders** — Automated payment nudges | Higher collection rate | 3 days |

### Phase 4: Enterprise & Data Products (Month 4-6)
**Goal: Enterprise contracts, API revenue, data monetization**

| Feature | Revenue Impact | Effort |
|---------|---------------|--------|
| **Enterprise API** — RESTful API for banks, SACCOs, insurers | KES 25K-150K/mo | 3 weeks |
| **API key management portal** — Self-service for enterprise | Included in API | 1 week |
| **Webhook system** — Real-time event notifications | Enterprise value | 1 week |
| **Bulk verification API** — Portfolio verification for banks | Enterprise value | 2 weeks |
| **Market analytics reports** — Aggregated property data | KES 10K-50K/report | 2 weeks |
| **Automated Valuation Model** — AI-powered valuations | KES 200-500/valuation | 2 weeks |
| **Fraud blacklist API** — Phone/email/title deed check | Enterprise value | 1 week |
| **Property comparison tool** — Side-by-side analysis | Buyer engagement | 3 days |
| **Map-based search** — Geospatial property discovery | Buyer engagement | 1 week |

### Phase 5: Scale Across Africa (Month 7-12)
**Goal: Multi-country, defensible data moat**

| Feature | Impact |
|---------|--------|
| **Tanzania launch** — Dar es Salaam, Arusha | Market expansion |
| **Uganda launch** — Kampala | Market expansion |
| **Nigeria prep** — Lagos, Abuja research | Market research |
| **Multi-currency support** — Support TZS, UGX, NGN | Infrastructure |
| **Multi-language support** — Swahili, French | Accessibility |
| **Mobile apps** — React Native or Capacitor | Distribution |
| **Land registry integrations** — Government API partnerships | Defensibility |
| **Bank partnerships** — Mortgage pre-qualification, title insurance | Revenue |
| **Insurance partnerships** — Rent guarantee, property insurance | Revenue |

---

## 10. GO-TO-MARKET STRATEGY — KENYA LAUNCH

### Target Segments (In Order)

1. **Real Estate Agents (Primary)** — 20,000+ registered agents in Kenya
   - Pain: Hard to prove they're legitimate, hard to stand out, no digital tools
   - Offer: Free badge for first 90 days, then KES 1,500/mo Basic
   - Acquisition: Visit 50 top agencies in Nairobi in person + WhatsApp groups

2. **Landlords (Secondary)** — Especially those with 5-50 units
   - Pain: Rent collection is manual, no tenant records, maintenance chaos
   - Offer: Free for first 2 units, KES 1,000/mo for up to 10
   - Acquisition: Property manager associations, Facebook landlord groups

3. **Property Buyers (Tertiary)** — Middle-class Kenyans
   - Pain: Can't trust listings, fear of fraud, no transparency
   - Offer: Free property search, pay only for verification reports
   - Acquisition: SEO, social media, WhatsApp, referrals

### Launch City: Nairobi (Start Here)

**Why Nairobi first:**
- 5M+ population, most active real estate market in East Africa
- Highest concentration of agents, developers, and buyers
- Best internet connectivity and M-Pesa penetration
- Hub for banks, SACCOs, insurance companies (enterprise clients)

**Then expand to:** Mombasa (Month 3) → Kisumu (Month 5) → Nakuru (Month 6) → Eldoret (Month 8)

### Agent Onboarding Strategy

```
Week 1-2: Direct outreach
- Visit 50 top Nairobi agencies in person (Westlands, Kilimani, Karen, Lavington, Runda)
- Demo the platform on a tablet
- Offer: "First 100 agents get Premium free for 3 months"
- Ask: "What's your biggest headache? How can we help?"

Week 3-4: WhatsApp acquisition
- Join 50+ Kenyan real estate WhatsApp groups
- Share helpful content (not spam): "How to spot a fake title deed" infographic
- Offer free property trust check for any listing
- Track referral codes

Month 2: Field team
- Hire 2 part-time agents (KES 15K/month + commission)
- They visit agencies, onboard agents, collect feedback
- Each field agent covers one zone of Nairobi

Month 3: Agent events
- Host free "Digital Real Estate Workshop" in Nairobi
- Teach: digital marketing, fraud prevention, using tech to close more deals
- Pitch VESTRA as the tool that makes it all easy
```

### Landlord Onboarding Strategy

```
- Target: Landlords with 5-50 units (too big for manual, too small for enterprise software)
- Channels: Kenya Landlords Association, Facebook groups, property management firms
- Hook: "Collect rent via M-Pesa automatically. Get paid on time, every time."
- Offer: Free rent collection for first 3 months (platform fee waived)
- Content: "The landlord's guide to digital rent collection" (PDF/WhatsApp)
```

### Buyer/Renter Trust Campaign

```
- Launch with: "Don't buy a fake property. Verify first."
- Content series:
  1. "5 signs a property listing is fake" (WhatsApp/Instagram)
  2. "How to verify a title deed in Kenya" (blog/YouTube)
  3. "Real stories: Kenyans who lost money to property fraud" (case studies)
- Offer: "First verification report free" for new users
- SEO: Target "buy property in Nairobi safely", "verify title deed Kenya", etc.
```

### WhatsApp Acquisition Funnel

WhatsApp is the #1 platform in Kenya. This is your biggest growth lever.

```
1. User sees VESTRA ad/link → "Message us on WhatsApp"
2. WhatsApp bot greets them: "Welcome to VESTRA! Are you looking to buy, rent, or sell?"
3. Bot asks discovery questions, shows relevant properties
4. Bot offers free trust check for any property they're interested in
5. User uploads listing link or phone number → VESTRA checks it
6. If property is on VESTRA: "This property is VESTRA-verified! Trust score: 85/100"
7. If property is not on VESTRA: "We couldn't verify this. Be careful. Want us to check it?"
8. User registers → receives referral code → "Share with friends, earn KES 200 each"
```

### Partnerships (Month 1-3)

| Partner | Why | Ask |
|---------|-----|-----|
| **Safaricom** | M-Pesa integration, co-marketing | Already integrated; explore Daraja partner program |
| **Kenya Bankers Association** | Mortgage data, bank partnerships | Introduction to member banks |
| **Nairobi County Government** | Land rates data, permits | Data access agreement |
| **ARDHI SASA (Ministry of Lands)** | Land registry digitization | API integration partnership |
| **Property Kenya / BuyRentKenya** | Listing aggregators | Data partnership or acquisition |
| **University of Nairobi Real Estate Dept** | Research, credibility | Joint research on property fraud |
| **Kenya Real Estate Agents Association** | Agent network | Official verification partner |
| **SACCO Societies Regulatory Authority** | SACCO partnerships | Introduction to top SACCOs |

### Pricing & Launch Offers

**Launch Offers (First 90 Days):**
- Agents: Premium tier free for 3 months (KES 15,000 value)
- Landlords: Pro tier free for 3 months (KES 3,500/mo value)
- Buyers: First verification report free (KES 500 value)
- Sellers: First 3 listings free (KES 900 value)
- Referral: Referrer gets KES 200, referred gets KES 200 credit

**After Launch Period (Month 4+):**
- Standard pricing per revenue model above
- Annual billing: 20% discount
- Enterprise: Custom pricing based on volume

---

## 11. 30/60/90 DAY EXECUTION PLAN

### Days 1-7: Security & Stability Sprint

| Day | Task | Files | Why |
|-----|------|-------|-----|
| 1 | Fix M-Pesa callback auth | `api/routes/payments.py` | Prevent fake payments |
| 1 | Fix WhatsApp broadcast auth | `api/routes/whatsapp.py` | Prevent spam/abuse |
| 1 | Add auth to AI endpoints | `api/routes/ai_routes.py` | Prevent resource abuse |
| 1 | Fix `next.config.ts` images | `next.config.ts` | SSRF prevention |
| 1 | Fix `upgrade_subscription` await | `services/subscription_service.py` | Critical bug fix |
| 1 | Fix `count_users` duplicate | `services/user_service.py` | Stats accuracy |
| 1 | Fix `__init__.py` model exports | `models/__init__.py` | Developer experience |
| 2 | Add database SSL config | `core/config.py`, `.env` | Data security |
| 2 | Add Redis auth | `core/config.py`, `docker-compose.yml` | Infrastructure security |
| 2 | Add `run_in_executor` for AI | `services/ai_service.py`, `valuation_service.py`, `whatsapp_service.py` | Performance |
| 2 | Add M-Pesa token caching | `services/mpesa_service.py` | Performance + reliability |
| 2 | Fix currency fields: Float→Numeric | All model files | Financial accuracy |
| 3 | Fix frontend `filters` re-render | `app/market/page.tsx` | UX bug |
| 3 | Fix pagination limit | `app/market/page.tsx` | UX bug |
| 3 | Fix email base URL config | `services/email_service.py` | Broken links fix |
| 3 | Add `.dockerignore` files | `backend/.dockerignore`, `frontend-build/.dockerignore` | Build efficiency |
| 4 | Add CAPTCHA to registration | `app/auth/register/page.tsx`, backend validation | Bot prevention |
| 4 | Add account lockout | `services/user_service.py`, `api/routes/auth.py` | Brute force protection |
| 4 | Set up Sentry | `main.py`, sentry_sdk init | Error tracking |
| 5 | Write auth integration tests | `tests/test_auth.py` | Regression safety |
| 5 | Write payment integration tests | `tests/test_payments.py` | Revenue safety |
| 6 | Fix Render deployment config | `render.yaml` | Deployment fix |
| 6 | Set up CI test job | `.github/workflows/ci-cd.yml` | Quality gate |
| 7 | Security penetration test (manual) | Full system | Launch readiness |
| 7 | Load test critical endpoints | `/api/auth/login`, `/api/properties/`, `/api/payments/mpesa/initiate` | Scale readiness |

**Deliverable: Production-ready, secure, tested platform.**

### Days 8-14: Revenue Sprint

| Day | Task | New Files |
|-----|------|-----------|
| 8-9 | **Paid verification reports** — Full M-Pesa payment → AI analysis → results → PDF report | `services/report_service.py`, `api/routes/reports.py` |
| 10 | **Listing fees** — Track free listings, charge beyond free tier | Update `property_service.py`, `api/routes/properties.py` |
| 10 | **Featured listings** — Payment → boost → badge | Update `property_service.py` |
| 11-12 | **Agent dashboard** — Listings overview, leads, earnings, subscription management | `app/dashboard/agent/page.tsx`, sub-pages |
| 12-13 | **Subscription plan UI** — Plan comparison, upgrade/downgrade flow | `app/subscriptions/page.tsx` |
| 14 | **PDF trust report generation** — Downloadable, branded verification report | `services/report_service.py`, `api/routes/reports.py` |

**Deliverable: First revenue-generating features live.**

### Days 15-21: Trust & Engagement Sprint

| Day | Task | New Files |
|-----|------|-----------|
| 15-16 | **KYC verification flow** — ID upload, selfie, OCR, admin review | `models/kyc.py`, `services/kyc_service.py`, `api/routes/kyc.py`, frontend KYC components |
| 17 | **Notifications system** — Email + in-app alerts | `models/notification.py`, `services/notification_service.py`, `api/routes/notifications.py` |
| 18 | **Saved properties & searches** — Favorites + alerts | `models/saved_property.py`, `models/saved_search.py`, frontend pages |
| 19-20 | **In-app messaging** — Buyer-seller-agent chat | `models/message.py`, `services/messaging_service.py`, `api/routes/messages.py`, chat UI |
| 21 | **Agent verification badges** — Visual trust indicators | Update `AgentProfile`, badge display components |

**Deliverable: Users trust the platform, engage deeply, and return.**

### Days 22-30: Growth & Polish Sprint

| Day | Task |
|-----|------|
| 22-23 | **WhatsApp property sharing** — One-click share to WhatsApp with rich preview |
| 24 | **Referral program activation** — Fix referral engine, add payout support, launch |
| 25 | **Landing page optimization** — Real testimonials, stats, Kenyan-specific content |
| 26-27 | **SEO** — Meta tags, structured data, sitemap, Kenyan city landing pages |
| 28 | **Analytics** — Google Analytics, custom event tracking, conversion funnels |
| 29 | **Mobile optimization** — Test on low-end Android phones, optimize load times |
| 30 | **Launch preparation** — Terms of Service, Privacy Policy, support workflow, social media setup |

**Deliverable: Platform is live, discoverable, shareable, and growing.**

### Month 2 (Days 31-60): Rental & Property Management

| Week | Tasks |
|------|-------|
| 5 | Automated rent collection — M-Pesa STK Push for monthly rent, late fee calculation |
| 6 | Rent dashboard — Payment tracking, arrears, receipts, collection rate analytics |
| 7 | Lease management — Digital lease creation, e-signature integration, renewal reminders |
| 8 | Maintenance marketplace — Request tracking, contractor assignment, cost tracking |

### Month 3 (Days 61-90): Enterprise & Defensibility

| Week | Tasks |
|------|-------|
| 9 | Enterprise API — RESTful API with key management, rate limiting, documentation |
| 10 | Tenant screening — Background checks, payment history, credit scoring |
| 11 | Market analytics — Aggregated property data reports, trend analysis |
| 12 | Agent directory — Public agent profiles with reviews, badges, deal history |

---

## 12. PRODUCTION CHECKLIST — BEFORE GOING LIVE

### Security (Non-Negotiable)

- [ ] M-Pesa callback authenticated (IP whitelist + HMAC signature)
- [ ] All admin endpoints behind role-based auth (not just UI hiding)
- [ ] Database SSL enforced (`?ssl=require`)
- [ ] Redis password set + TLS if available
- [ ] SECRET_KEY changed from default (min 64 chars, random)
- [ ] JWT tokens have reasonable expiry (60 min access, 7 day refresh)
- [ ] Rate limiting on all auth endpoints (login, register, forgot-password)
- [ ] Rate limiting on AI endpoints
- [ ] CAPTCHA on registration
- [ ] Account lockout after 5 failed login attempts (15 min window)
- [ ] CSP headers reviewed (remove `unsafe-inline` if possible)
- [ ] HSTS enabled with preload
- [ ] CORS origins locked to production domains only
- [ ] File upload: MIME type validation, size limits, no executable files
- [ ] File upload: Virus scanning (ClamAV or cloud scanning)
- [ ] No secrets in code, config files, or Docker images
- [ ] All secrets via environment variables or secrets manager
- [ ] Dependency vulnerability scan (Dependabot, Snyk, or pip-audit)
- [ ] SQL injection: All queries use parameterized SQL (verification done — but re-check search_service raw SQL)
- [ ] XSS: React's escaping + CSP headers
- [ ] CSRF: Token-based protection for state-changing operations (config flag exists but middleware missing)
- [ ] OWASP ZAP baseline scan clean
- [ ] Penetration test on payment flow, auth flow, admin endpoints

### Payments (Non-Negotiable)

- [ ] M-Pesa sandbox testing completed (all scenarios: success, failure, timeout, duplicate callback)
- [ ] M-Pesa production credentials obtained from Safaricom
- [ ] M-Pesa production shortcode registered and approved
- [ ] Callback URL is HTTPS (required by Safaricom for production)
- [ ] Payment reconciliation process defined (daily check against M-Pesa statements)
- [ ] Refund process documented and tested
- [ ] Payment failure handling: user gets clear error, payment record is accurate
- [ ] Idempotency: Duplicate M-Pesa callbacks don't double-credit
- [ ] Payment logging: Every payment event logged with correlation ID
- [ ] Daily revenue reconciliation alert (Slack/email)

### Legal & Compliance

- [ ] Terms of Service drafted (Kenyan law, include Data Protection Act 2019 compliance)
- [ ] Privacy Policy drafted (what data is collected, how it's used, user rights)
- [ ] Cookie policy (if using non-essential cookies)
- [ ] Data Protection Act 2019 compliance review (appoint Data Protection Officer if needed)
- [ ] User consent for data collection (explicit opt-in for marketing)
- [ ] Right to deletion (GDPR-style, even though Kenya DPA)
- [ ] Data breach notification process defined (72-hour requirement under DPA 2019)
- [ ] Business registration: VESTRA legally registered in Kenya
- [ ] KRA PIN for business (required for M-Pesa business till)
- [ ] M-Pesa business till number obtained
- [ ] Terms cover: user responsibilities, listing accuracy, payment disputes, platform liability limits
- [ ] Agent agreement: code of conduct, verification requirements, commission structure
- [ ] Property listing guidelines: what can/cannot be listed, accuracy requirements

### Data Protection

- [ ] Database backups: Daily automated, encrypted, tested restore
- [ ] Backups stored in different region from primary
- [ ] PII encryption at rest (national_id, phone numbers)
- [ ] Data retention policy: how long is user data kept after account deletion?
- [ ] Access control: Who can see what data? (admin roles, support access)
- [ ] Audit logging: All data access by staff is logged
- [ ] Data export: Users can request their data (DPA requirement)
- [ ] Cookie consent banner (if using analytics cookies)

### Monitoring & Observability

- [ ] Application monitoring: Sentry or similar (error tracking, performance)
- [ ] Uptime monitoring: UptimeRobot, Better Uptime, or Pingdom (every 1 min)
- [ ] API metrics: Prometheus + Grafana (already partially set up)
- [ ] Business metrics: Daily active users, new listings, verifications, revenue
- [ ] Database monitoring: Slow query log, connection pool usage, disk space
- [ ] Redis monitoring: Memory usage, hit rate, connection count
- [ ] M-Pesa API monitoring: Success rate, latency, error types
- [ ] Alerting: PagerDuty/OpsGenie or simple Slack/WhatsApp alerts
- [ ] Status page: status.vestra.co.ke (or use a hosted service)
- [ ] Log aggregation: Structured JSON logs → centralized logging (ELK, Loki, or cloud)

### Admin Controls

- [ ] Admin dashboard: User management (view, suspend, delete)
- [ ] Admin dashboard: Property moderation (approve, reject, suspend)
- [ ] Admin dashboard: Verification review queue
- [ ] Admin dashboard: Payment/transaction view
- [ ] Admin dashboard: Dispute management
- [ ] Admin dashboard: Fraud report investigation
- [ ] Admin dashboard: System configuration (feature flags, pricing)
- [ ] Admin actions are all logged (who did what, when)
- [ ] Super admin vs admin role separation
- [ ] Admin audit log viewable (not deletable)

### Abuse Prevention

- [ ] Rate limiting on all public endpoints
- [ ] Listing creation limits: max per user per day
- [ ] Duplicate listing detection: same images, same title, same phone
- [ ] Profanity filter on listing titles/descriptions
- [ ] Image moderation: no inappropriate content (consider Google Vision API or similar)
- [ ] Report/flag mechanism: users can report suspicious listings
- [ ] Automated suspension: Too many reports → auto-flag for review
- [ ] IP blacklist for known abusers
- [ ] Phone number reputation: check against fraud reports

### Support Workflows

- [ ] Support email: help@vestra.co.ke (or similar)
- [ ] WhatsApp support: Dedicated business number
- [ ] Response time SLA: < 4 hours during business hours
- [ ] Ticket system: Simple CRM or even shared inbox to start
- [ ] FAQ/Help Center: At minimum, a Notion page or simple static page
- [ ] Common issues documented: "How to verify a property", "How to pay via M-Pesa"
- [ ] Escalation path: Support → Admin → Founder
- [ ] Refund policy: When and how refunds are processed
- [ ] Dispute resolution process: Step-by-step for buyers and sellers

### Deployment

- [ ] Production domain: vestra.co.ke (or similar) registered
- [ ] SSL certificate: Let's Encrypt or cloud-managed
- [ ] DNS configured: A/AAAA records, CNAME for www
- [ ] Email configured: SPF, DKIM, DMARC (for transactional emails)
- [ ] CDN configured: Cloudflare (free tier) for DDoS protection + caching
- [ ] Database backups automated and tested
- [ ] Deployment pipeline: GitHub Actions → deploy on push to main
- [ ] Rollback plan: How to revert to previous version in < 5 minutes
- [ ] Staging environment: Separate from production, test changes before deploy
- [ ] Database migrations run automatically as part of deploy

### Analytics

- [ ] Google Analytics or Plausible (privacy-friendly)
- [ ] Conversion tracking: Visitor → Register → List → Verify → Pay
- [ ] Funnel analysis: Where do users drop off?
- [ ] Cohort analysis: Which acquisition channel has best retention?
- [ ] Revenue tracking: MRR, ARPU, churn rate, LTV
- [ ] Property analytics: Views, inquiries, time-to-sell, price trends
- [ ] User behavior: Search patterns, popular filters, feature usage

---

## 13. FINAL PRIORITIZED CHECKLIST

### CRITICAL (Fix Before Anything Else — Days 1-3)

1. [ ] **M-Pesa callback authentication** — Current: anyone can POST fake payments. Fix: IP whitelist + HMAC
2. [ ] **WhatsApp broadcast auth** — Current: any user can broadcast. Fix: change to admin-only
3. [ ] **AI endpoint authentication** — Current: open to the world. Fix: add auth + rate limiting
4. [ ] **`next.config.ts` image wildcard** — Current: `hostname: '**'`. Fix: allow only known hosts
5. [ ] **`upgrade_subscription` await bug** — Current: returns coroutine, not string. Fix: add `await`
6. [ ] **`count_users` duplicate** — Current: first definition unreachable. Fix: remove duplicate
7. [ ] **Docker Compose hardcoded secrets** — Current: default passwords. Fix: remove defaults, require env vars

### HIGH (Production Readiness — Days 1-7)

8. [ ] **Database SSL** — Add to connection string
9. [ ] **Redis auth** — Configure password
10. [ ] **`run_in_executor` for AI** — Fix blocking event loop
11. [ ] **M-Pesa token caching** — Don't fetch token per request
12. [ ] **Currency fields: Float → Numeric** — All money fields across all models
13. [ ] **Sentry error tracking** — Ship day 1
14. [ ] **CAPTCHA on registration** — Bot prevention
15. [ ] **Account lockout** — Brute force protection
16. [ ] **Email base URL fix** — Don't use CORS_ORIGINS
17. [ ] **Integration tests** — Auth + payments minimum
18. [ ] **Frontend `filters` re-render fix** — Market page
19. [ ] **Pagination fix** — Remove 5-page limit
20. [ ] **`.dockerignore` files** — For both backend and frontend

### MEDIUM (Revenue Enablement — Days 8-21)

21. [ ] **Paid verification report flow** — M-Pesa → AI → PDF report
22. [ ] **Agent subscription tiers** — Feature gating by plan
23. [ ] **Listing fees** — Beyond free tier
24. [ ] **Featured listings** — Payment → boost
25. [ ] **Agent dashboard** — Listings, leads, earnings
26. [ ] **Landlord dashboard** — Units, tenants, rent
27. [ ] **KYC verification flow** — ID upload, OCR, review
28. [ ] **Notification system** — Email + in-app
29. [ ] **In-app messaging** — Buyer-seller-agent
30. [ ] **PDF trust report** — Downloadable branded report
31. [ ] **Saved properties & searches** — Favorites + alerts
32. [ ] **Referral program fix** — DB-backed codes, payouts
33. [ ] **WhatApp property sharing** — One-click share
34. [ ] **Terms of Service + Privacy Policy** — Legal docs written
35. [ ] **Admin dashboard enrichment** — Verification queue, user management

### LOWER (Growth & Scale — Days 22-60)

36. [ ] **SEO optimization** — City pages, structured data, sitemap
37. [ ] **WhatsApp property assistant** — Inbound lead gen bot
38. [ ] **Rent collection automation** — M-Pesa monthly billing
39. [ ] **Lease management** — Digital leases, e-signatures
40. [ ] **Maintenance tracking** — Request → Assign → Complete
41. [ ] **Tenant screening** — Background check reports
42. [ ] **Enterprise API** — RESTful API with key management
43. [ ] **Map-based search** — Geospatial property discovery
44. [ ] **Property comparison** — Side-by-side analysis
45. [ ] **Market analytics** — Aggregated data reports
46. [ ] **Agent directory** — Public profiles, reviews, badges
47. [ ] **Mobile app preparation** — PWA → Capacitor wrapper
48. [ ] **Data collection pipeline** — For future ML models

### BACKLOG (Month 3+)

49. [ ] **Escrow/deposit protection** — Secure transaction holding
50. [ ] **Dispute resolution system** — Mediation workflow
51. [ ] **Fraud blacklist** — Cross-reference phone/email/title deed
52. [ ] **ML models** — Price prediction, fraud detection, tenant scoring
53. [ ] **Bank partnerships** — Mortgage pre-qualification API
54. [ ] **Insurance partnerships** — Rent guarantee, title insurance
55. [ ] **Land registry integration** — ArdhiSasa API
56. [ ] **Multi-currency support** — TZS, UGX, NGN
57. [ ] **Swahili localization** — Full app translation
58. [ ] **WhatsApp Commerce** — Browse + pay entirely in WhatsApp
59. [ ] **Tanzania launch** — Dar es Salaam
60. [ ] **Mobile apps** — iOS + Android native or React Native

---

## CONCLUSION

VESTRA is a **genuinely good foundation** — better architected than 90% of MVPs in this space. The security infrastructure (IP-bound JWT, rate limiting, structured logging, Prometheus metrics) is impressive. The models cover the core real estate domain well.

**Your immediate advantage:** You have working code for M-Pesa payments, property listings, AI verification, rental management, WhatsApp integration, and subscriptions — all the hard parts are scaffolded. Now you need to:
1. Fix the critical security gaps (this week)
2. Wire up the revenue features (next 2 weeks)
3. Launch to Nairobi agents (week 3-4)
4. Add rent collection + enterprise features (month 2-3)
5. Build the data moat (month 3-6)

**The biggest risk is not technical — it's go-to-market.** The best platform in the world fails if agents don't use it. Spend at least 40% of your time on agent onboarding, field visits, and WhatsApp community building in the first 90 days.

**The biggest opportunity:** Kenya's real estate market is broken, and no one has solved trust at scale. VESTRA can become the "M-Pesa of real estate" — the platform everyone trusts because it actually verifies things. That brand moat is worth more than any single feature.

**Revenue isn't optional — it's the engine that makes everything else possible.** Start charging from week 2. Free tiers exist only to drive paid conversion. Every feature should have a clear path to revenue.

**Good luck. Now go build.** 🇰🇪
