// User types
export type UserRole = 'buyer' | 'seller' | 'agent' | 'landlord' | 'admin' | 'super_admin';

export interface User {
  id: number;
  email: string;
  phone?: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  is_kyc_verified: boolean;
  avatar_url?: string;
  location?: string;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

// Property types
export type PropertyType = 'residential' | 'commercial' | 'land' | 'industrial' | 'agricultural' | 'student_housing' | 'short_stay';
export type ListingType = 'sale' | 'rent' | 'lease';
export type PropertyStatus = 'draft' | 'pending_review' | 'active' | 'suspended' | 'sold' | 'rented';

export interface Property {
  id: number;
  owner_id: number;
  owner_name?: string;
  owner_phone?: string;
  title: string;
  description?: string;
  property_type: PropertyType;
  listing_type: ListingType;
  status: PropertyStatus;
  address: string;
  city: string;
  county: string;
  country: string;
  latitude?: number;
  longitude?: number;
  price: number;
  currency: string;
  price_negotiable: boolean;
  bedrooms?: number;
  bathrooms?: number;
  size_sqft?: number;
  year_built?: number;
  amenities: string[];
  images: string[];
  trust_score?: number;
  is_verified: boolean;
  verification_badge?: 'bronze' | 'silver' | 'gold' | 'platinum';
  is_featured: boolean;
  featured_expires_at?: string;
  views: number;
  inquiries: number;
  created_at: string;
  updated_at?: string;
}

export interface PropertyListResponse {
  items: Property[];
  total: number;
  page: number;
  pages: number;
  size: number;
}

export interface PropertyCreate {
  title: string;
  description?: string;
  property_type: PropertyType;
  listing_type: ListingType;
  address: string;
  city: string;
  county: string;
  price: number;
  currency?: string;
  price_negotiable?: boolean;
  bedrooms?: number;
  bathrooms?: number;
  size_sqft?: number;
  year_built?: number;
  amenities?: string[];
  images?: string[];
}

// Verification types
export type VerificationStatus = 'pending' | 'in_progress' | 'approved' | 'flagged' | 'rejected';

export interface Verification {
  id: number;
  property_id?: number;
  status: VerificationStatus;
  fraud_risk_score?: number;
  trust_score?: number;
  price_reasonableness?: 'under' | 'fair' | 'over';
  ownership_confidence?: 'low' | 'medium' | 'high';
  ai_recommendation?: 'approve' | 'review' | 'reject';
  document_flags: string[];
  ai_summary?: string;
  report_url?: string;
  created_at: string;
  updated_at?: string;
}

// Payment types
export type PaymentStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'refunded';
export type PaymentMethod = 'mpesa' | 'stripe' | 'bank_transfer';
export type PaymentPurpose = 'verification_report' | 'agent_badge' | 'listing_fee' | 'subscription' | 'transaction_fee' | 'rent' | 'deposit' | 'utility';

export interface Payment {
  id: number;
  amount: number;
  currency: string;
  method: PaymentMethod;
  purpose: PaymentPurpose;
  status: PaymentStatus;
  reference?: string;
  mpesa_checkout_request_id?: string;
  mpesa_receipt_number?: string;
  phone_number?: string;
  description?: string;
  created_at: string;
}

// Admin stats
export interface ChartDataPoint {
  month: string;
  revenue?: number;
  count?: number;
  verifications?: number;
  listings?: number;
  users?: number;
}

export interface DistributionItem {
  name: string;
  value: number;
  color: string;
}

export interface RecentUser {
  id: number; email: string; full_name: string;
  role: string; is_active: boolean; created_at: string;
}

export interface RecentProperty {
  id: number; title: string; city: string; price: number;
  status: string; trust_score: number | null; is_verified: boolean;
  created_at: string;
}

export interface PendingReview {
  id: number; property_id: number | null;
  fraud_risk_score: number | null; trust_score: number | null;
  ai_recommendation: string | null; status: string;
  created_at: string;
}

export interface AdminStats {
  total_users: number;
  total_properties: number;
  total_verifications: number;
  total_revenue: number;
  pending_verifications: number;
  active_listings: number;
  verified_properties: number;
  agents_count: number;
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

// Search
export interface PropertySearch {
  query?: string;
  city?: string;
  county?: string;
  property_type?: PropertyType;
  listing_type?: ListingType;
  min_price?: number;
  max_price?: number;
  bedrooms?: number;
  verified_only?: boolean;
  page?: number;
  size?: number;
}

export interface AISearchResult {
  interpretation: string;
  filters_applied: Record<string, unknown>;
  items: Property[];
  total: number;
  page: number;
  pages: number;
  size: number;
  market_context?: string;
  ai_recommendations?: string[];
  search_tips?: string[];
}

// Escrow types
export type EscrowStatus = 'initiated' | 'deposit_paid' | 'balance_paid' | 'completed' | 'cancelled' | 'refunded' | 'disputed';

export interface EscrowTransaction {
  id: number;
  property_id: number;
  buyer_id: number;
  seller_id: number;
  agent_id?: number;
  amount_kes: number;
  deposit_amount_kes?: number;
  status: EscrowStatus;
  payment_reference?: string;
  release_condition_met: boolean;
  completion_date?: string;
  terms?: string;
  created_at: string;
  updated_at?: string;
}

// Dispute types
export type DisputeStatus = 'open' | 'investigating' | 'resolved' | 'closed';

export interface Dispute {
  id: number;
  reporter_id: number;
  property_id?: number;
  subject_type?: string;
  subject_id?: number;
  category: string;
  description: string;
  evidence_urls: string[];
  status: DisputeStatus;
  resolution?: string;
  resolved_by_id?: number;
  resolved_at?: string;
  created_at: string;
  updated_at?: string;
}

// Review types
export interface Review {
  id: number;
  reviewer_id: number;
  subject_id: number;
  property_id?: number;
  rating: number;
  title?: string;
  body?: string;
  is_verified_transaction: boolean;
  created_at: string;
}

export interface SubjectReviews {
  subject_id: number;
  total_reviews: number;
  average_rating: number;
  positive_pct: number;
  reviews: Review[];
}

// Payout types
export type PayoutStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Payout {
  id: number;
  user_id: number;
  amount_kes: number;
  payout_type: string;
  status: PayoutStatus;
  mpesa_receipt?: string;
  reference_id?: number;
  reference_type?: string;
  description?: string;
  failure_reason?: string;
  processed_at?: string;
  completed_at?: string;
  created_at: string;
}

// KYC types
export type KYCStatus = 'not_submitted' | 'pending' | 'approved' | 'rejected';

export interface KYCVerification {
  id: number;
  user_id: number;
  status: KYCStatus;
  id_type: string;
  id_number?: string;
  rejection_reason?: string;
  reviewed_by_id?: number;
  reviewed_at?: string;
  created_at: string;
}

// Subscription types
export interface SubscriptionPlan {
  tier: string;
  price: number;
  features: string[];
  max_listings: number;
  badge?: string;
}

export interface UserSubscription {
  id: number;
  user_id: number;
  tier: string;
  status: string;
  amount_kes: number;
  auto_renew: boolean;
  current_period_end?: string;
  grace_period_end?: string;
  renewal_failures: number;
}

// Enterprise types
export interface APIKeyInfo {
  id: number;
  name: string;
  prefix: string;
  scopes: string[];
  is_active: boolean;
  rate_limit_per_min: number;
  last_used_at?: string;
  expires_at?: string;
  created_at: string;
}

export interface WebhookInfo {
  id: number;
  url: string;
  events: string[];
  is_active: boolean;
  failures: number;
  last_success?: string;
}

// Notification types
export interface Notification {
  id: number;
  user_id: number;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  action_url?: string;
  created_at: string;
}

// Message types
export interface Conversation {
  other_user_id: number;
  other_user_name: string;
  other_user_avatar?: string;
  last_message: string;
  last_message_at: string;
  unread_count: number;
}

export interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  body: string;
  is_read: boolean;
  created_at: string;
}

// Vestima Price Estimator types
export interface VestimaComparable {
  title: string;
  price: number;
  size_sqft: number | null;
  price_per_sqft: number;
  bedrooms: number | null;
  location: string;
  distance_km: number | null;
  relevance_score: number;
  is_verified: boolean;
}

export interface VestimaEstimate {
  estimated_value: number;
  low_estimate: number;
  high_estimate: number;
  confidence_score: number;
  confidence_label: 'high' | 'medium' | 'low';
  comparables: VestimaComparable[];
  price_per_sqft: number | null;
  market_trend: 'appreciating' | 'stable' | 'declining';
  market_status: string;
  valuation_summary: string;
  as_of: string;
}

export interface VestimaHistoryEntry {
  estimated_value: number;
  low_estimate: number;
  high_estimate: number;
  confidence_score: number;
  as_of: string;
  months_ago: number;
}
