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

export interface Payment {
  id: number;
  amount: number;
  currency: string;
  method: PaymentMethod;
  purpose: string;
  status: PaymentStatus;
  reference?: string;
  mpesa_checkout_request_id?: string;
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
}
