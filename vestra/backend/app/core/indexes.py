"""
Database index creation for production performance.
Run once during startup to ensure all performance indexes exist.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra")

PERFORMANCE_INDEXES = [
    # ── pg_trgm extension (for fast ILIKE with leading % wildcards) ──
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    # Properties — search and filtering
    "CREATE INDEX IF NOT EXISTS idx_properties_status ON properties (status)",
    "CREATE INDEX IF NOT EXISTS idx_properties_city ON properties (city)",
    "CREATE INDEX IF NOT EXISTS idx_properties_county ON properties (county)",
    "CREATE INDEX IF NOT EXISTS idx_properties_price ON properties (price)",
    "CREATE INDEX IF NOT EXISTS idx_properties_type ON properties (property_type)",
    "CREATE INDEX IF NOT EXISTS idx_properties_listing_type ON properties (listing_type)",
    "CREATE INDEX IF NOT EXISTS idx_properties_bedrooms ON properties (bedrooms)",
    "CREATE INDEX IF NOT EXISTS idx_properties_trust ON properties (trust_score)",
    "CREATE INDEX IF NOT EXISTS idx_properties_verified ON properties (is_verified)",
    "CREATE INDEX IF NOT EXISTS idx_properties_created ON properties (created_at DESC)",
    # Composite indexes for common queries
    "CREATE INDEX IF NOT EXISTS idx_properties_status_city ON properties (status, city)",
    "CREATE INDEX IF NOT EXISTS idx_properties_type_status ON properties (property_type, status)",
    "CREATE INDEX IF NOT EXISTS idx_properties_owner_status ON properties (owner_id, status)",
    # Listing default sort: WHERE status='active' ORDER BY is_featured DESC, created_at DESC
    "CREATE INDEX IF NOT EXISTS idx_properties_status_featured_created ON properties (status, is_featured DESC, created_at DESC)",
    # User's properties sorted by date
    "CREATE INDEX IF NOT EXISTS idx_properties_owner_created ON properties (owner_id, created_at DESC)",
    # ── pg_trgm GIN indexes (fast ILIKE %search% with leading wildcard) ──
    "CREATE INDEX IF NOT EXISTS idx_users_name_trgm ON users USING gin (full_name gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_users_email_trgm ON users USING gin (email gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_properties_city_trgm ON properties USING gin (city gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_properties_county_trgm ON properties USING gin (county gin_trgm_ops)",
    # Users
    "CREATE INDEX IF NOT EXISTS idx_users_role ON users (role)",
    "CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active)",
    "CREATE INDEX IF NOT EXISTS idx_users_created ON users (created_at DESC)",
    # Verifications
    "CREATE INDEX IF NOT EXISTS idx_verifications_status ON verifications (status)",
    "CREATE INDEX IF NOT EXISTS idx_verifications_property ON verifications (property_id)",
    "CREATE INDEX IF NOT EXISTS idx_verifications_requester ON verifications (requester_id)",
    # Payments
    "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments (status)",
    "CREATE INDEX IF NOT EXISTS idx_payments_user ON payments (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_created ON payments (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_payments_checkout ON payments (mpesa_checkout_request_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_purpose ON payments (purpose)",
    # Documents
    "CREATE INDEX IF NOT EXISTS idx_documents_property ON documents (property_id)",
    "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents (document_type)",
    "CREATE INDEX IF NOT EXISTS idx_documents_uploader ON documents (uploader_id)",
    # Subscriptions
    "CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions (status)",
    "CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON subscriptions (tier)",
    "CREATE INDEX IF NOT EXISTS idx_subscriptions_period_end ON subscriptions (current_period_end)",
    # Referrals
    "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals (referrer_id)",
    "CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals (referred_user_id)",
    "CREATE INDEX IF NOT EXISTS idx_referral_rewards_ref ON referral_rewards (referrer_id)",
    # Title Chain
    "CREATE INDEX IF NOT EXISTS idx_title_chain_property ON title_chain_blocks (property_id, block_index)",
    "CREATE INDEX IF NOT EXISTS idx_title_chain_hash ON title_chain_blocks (block_hash)",
    # Rental Units
    "CREATE INDEX IF NOT EXISTS idx_rental_units_landlord ON rental_units (landlord_id)",
    # Tenants
    "CREATE INDEX IF NOT EXISTS idx_tenants_unit ON tenants (unit_id)",
    "CREATE INDEX IF NOT EXISTS idx_tenants_phone ON tenants (phone)",
    # Leases
    "CREATE INDEX IF NOT EXISTS idx_leases_unit ON leases (unit_id)",
    "CREATE INDEX IF NOT EXISTS idx_leases_tenant ON leases (tenant_id)",
    # Rent Payments
    "CREATE INDEX IF NOT EXISTS idx_rent_payments_tenant ON rent_payments (tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rent_payments_month ON rent_payments (month)",
    "CREATE INDEX IF NOT EXISTS idx_rent_payments_status ON rent_payments (status)",
    # Maintenance
    "CREATE INDEX IF NOT EXISTS idx_maintenance_unit ON maintenance_requests (unit_id)",
    "CREATE INDEX IF NOT EXISTS idx_maintenance_status ON maintenance_requests (status)",
    # Audit Logs
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs (resource_type, resource_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs (created_at DESC)",
    # Full-text search index (GIN) — might already exist
    "CREATE INDEX IF NOT EXISTS idx_properties_fts ON properties USING gin(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(address,'') || ' ' || coalesce(city,'') || ' ' || coalesce(county,'')))",
    # Payments — user payments sorted by date (high-traffic: /payments/my)
    "CREATE INDEX IF NOT EXISTS idx_payments_user_created ON payments (user_id, created_at DESC)",
    # Notifications — unread fetch (high-traffic: polling for new notifications)
    "CREATE INDEX IF NOT EXISTS idx_notifications_user_read_created ON notifications (user_id, is_read, created_at DESC)",
    # Messages — conversation list (high-traffic: /messages)
    "CREATE INDEX IF NOT EXISTS idx_messages_sender_receiver_created ON messages (sender_id, receiver_id, created_at DESC)",
    # KYC — admin review queue (frequent admin page load)
    "CREATE INDEX IF NOT EXISTS idx_kyc_verifications_status_created ON kyc_verifications (status, created_at)",
    # Verifications — admin verification queue
    "CREATE INDEX IF NOT EXISTS idx_verifications_status_created ON verifications (status, created_at)",
    # Properties — featured active listings (landing page / market top)
    "CREATE INDEX IF NOT EXISTS idx_properties_active_featured ON properties (status, is_featured DESC, created_at DESC) WHERE status = 'active'",
    # Enterprise — API key lookup (frequent middleware check)
    "CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys (key_hash)",
    # Disputes — user's disputes sorted
    "CREATE INDEX IF NOT EXISTS idx_disputes_filer_created ON disputes (filed_by_id, created_at DESC)",
    # Analytics — user events by type and time (dashboard charts)
    "CREATE INDEX IF NOT EXISTS idx_user_events_user_type_time ON user_events (user_id, event_type, created_at DESC)",
]


async def create_performance_indexes(db: AsyncSession):
    """Ensure all performance indexes exist. Safe to call on every startup."""
    for idx_sql in PERFORMANCE_INDEXES:
        try:
            await db.execute(text(idx_sql))
        except Exception as e:
            logger.warning('{"index_error":"%s"}', str(e)[:100])
    await db.commit()
    logger.info('{"indexes_ensured":%d}', len(PERFORMANCE_INDEXES))
