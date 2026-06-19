import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  AuthToken, User, Property, PropertyListResponse,
  PropertyCreate, Verification, Payment, AdminStats,
  PropertySearch, AISearchResult
} from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

// ── Retry helper ──────────────────────────────────────────────────────────────

function shouldRetry(error: AxiosError, attempt: number): boolean {
  // Retry on network errors and 5xx responses
  if (attempt >= MAX_RETRIES) return false;
  if (!error.response) return true; // Network error
  const status = error.response.status;
  if (status >= 500 && status < 600) return true; // Server error
  if (status === 429) return true; // Rate limited
  return false;
}

async function withRetry<T>(fn: () => Promise<T>, attempt = 0): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    const axiosErr = err as AxiosError;
    if (shouldRetry(axiosErr, attempt)) {
      const delay = RETRY_DELAY_MS * Math.pow(2, attempt); // Exponential backoff
      await new Promise((r) => setTimeout(r, delay));
      return withRetry(fn, attempt + 1);
    }
    throw err;
  }
}

// ── API Client ────────────────────────────────────────────────────────────────

class VestraAPIClient {
  client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: 30000,
      headers: { 'Content-Type': 'application/json' },
    });

    // Attach token and correlation ID
    this.client.interceptors.request.use((config) => {
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('vestra_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        // Add correlation ID for request tracing
        const correlationId = crypto.randomUUID?.()?.slice(0, 12) ||
          Math.random().toString(36).slice(2, 14);
        config.headers['X-Correlation-ID'] = correlationId;
      }
      return config;
    });

    // Response interceptor — handles expired tokens gracefully
    // Amazon-style: never force-redirect on public pages. Just clear stale tokens
    // and let individual page guards handle auth requirements.
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          if (typeof window !== 'undefined') {
            // Only force-redirect if user is on an explicitly auth-required path
            // Public pages (/, /market, /verify, etc.) should never redirect
            const path = window.location.pathname;
            const isAuthRequiredPath =
              path.startsWith('/account') ||
              path.startsWith('/dashboard') ||
              path.startsWith('/admin') ||
              path.startsWith('/properties/new') ||
              path.startsWith('/properties/edit') ||
              path.startsWith('/properties/my') ||
              path.startsWith('/messages') ||
              path.startsWith('/subscription') ||
              path.startsWith('/agents');

            // Clear stale auth data silently
            localStorage.removeItem('vestra_token');
            localStorage.removeItem('vestra_user');

            // Only redirect if AuthGuard would have required login anyway
            if (isAuthRequiredPath) {
              window.location.href = '/auth/login?redirect=' + encodeURIComponent(path);
            }
            // On public pages: just clear token, stay on page, let user browse freely
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // ─── Auth ──────────────────────────────────────────────────────────────────

  async register(data: {
    email: string; phone?: string; full_name: string;
    password: string; role?: string;
  }): Promise<AuthToken> {
    return withRetry(async () => {
      const res = await this.client.post<AuthToken>('/api/auth/register', data);
      return res.data;
    });
  }

  async login(email: string, password: string): Promise<AuthToken> {
    const res = await this.client.post<AuthToken>('/api/auth/login', { email, password });
    return res.data;
  }

  async getMe(): Promise<User> {
    return withRetry(async () => {
      const res = await this.client.get<User>('/api/auth/me');
      return res.data;
    });
  }

  async updateMe(data: Partial<User>): Promise<User> {
    const res = await this.client.put<User>('/api/auth/me', data);
    return res.data;
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    const res = await this.client.post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return res.data;
  }

  async forgotPassword(email: string): Promise<{ message: string }> {
    const res = await this.client.post('/api/auth/forgot-password', { email });
    return res.data;
  }

  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    const res = await this.client.post('/api/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return res.data;
  }

  async verifyEmail(token: string): Promise<{ message: string }> {
    const res = await this.client.post(`/api/auth/verify-email?token=${encodeURIComponent(token)}`);
    return res.data;
  }

  async resendVerification(email: string): Promise<{ message: string }> {
    const res = await this.client.post('/api/auth/resend-verification', null, {
      params: { email },
    });
    return res.data;
  }

  // ─── Properties ────────────────────────────────────────────────────────────

  async listProperties(params: PropertySearch = {}): Promise<PropertyListResponse> {
    return withRetry(async () => {
      const res = await this.client.get<PropertyListResponse>('/api/properties', { params });
      return res.data;
    });
  }

  async aiSearch(query: string): Promise<AISearchResult> {
    return withRetry(async () => {
      const res = await this.client.get<AISearchResult>('/api/properties/ai-search', {
        params: { q: query },
      });
      return res.data;
    });
  }

  async getProperty(id: number): Promise<Property> {
    return withRetry(async () => {
      const res = await this.client.get<Property>(`/api/properties/${id}`);
      return res.data;
    });
  }

  async createProperty(data: PropertyCreate): Promise<Property> {
    const res = await this.client.post<Property>('/api/properties', data);
    return res.data;
  }

  async updateProperty(id: number, data: Partial<PropertyCreate>): Promise<Property> {
    const res = await this.client.put<Property>(`/api/properties/${id}`, data);
    return res.data;
  }

  async publishProperty(id: number): Promise<Property> {
    const res = await this.client.post<Property>(`/api/properties/${id}/publish`);
    return res.data;
  }

  async deleteProperty(id: number): Promise<void> {
    await this.client.delete(`/api/properties/${id}`);
  }

  async getMyProperties(): Promise<Property[]> {
    return withRetry(async () => {
      const res = await this.client.get<Property[]>('/api/properties/my');
      return res.data;
    });
  }

  // ─── Verification ──────────────────────────────────────────────────────────

  async requestVerification(propertyId: number, phoneNumber: string): Promise<{
    payment_id: number; checkout_request_id?: string; message: string; amount: number;
  }> {
    const res = await this.client.post('/api/verify/request', {
      property_id: propertyId,
      phone_number: phoneNumber,
    });
    return res.data;
  }

  async runVerificationNow(propertyId: number): Promise<Verification> {
    const res = await this.client.post<Verification>(`/api/verify/run/${propertyId}`);
    return res.data;
  }

  async getVerificationStatus(id: number): Promise<Verification> {
    return withRetry(async () => {
      const res = await this.client.get<Verification>(`/api/verify/status/${id}`);
      return res.data;
    });
  }

  async getPropertyVerifications(propertyId: number): Promise<Verification[]> {
    return withRetry(async () => {
      const res = await this.client.get<Verification[]>(`/api/verify/property/${propertyId}`);
      return res.data;
    });
  }

  async uploadDocument(
    propertyId: number,
    documentType: string,
    file: File,
    onProgress?: (pct: number) => void
  ): Promise<{ id: number; file_name: string; message: string }> {
    const form = new FormData();
    form.append('property_id', String(propertyId));
    form.append('document_type', documentType);
    form.append('file', file);

    const res = await this.client.post('/api/verify/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    });
    return res.data;
  }

  // ─── Payments ──────────────────────────────────────────────────────────────

  async initiateMpesa(data: {
    phone_number: string; amount: number;
    purpose: string; reference_id?: number;
  }): Promise<{ payment_id: number; checkout_request_id?: string; message: string }> {
    const res = await this.client.post('/api/payments/mpesa/initiate', data);
    return res.data;
  }

  async getPaymentStatus(paymentId: number): Promise<Payment> {
    return withRetry(async () => {
      const res = await this.client.get<Payment>(`/api/payments/status/${paymentId}`);
      return res.data;
    });
  }

  async getMyPayments(): Promise<Payment[]> {
    return withRetry(async () => {
      const res = await this.client.get<Payment[]>('/api/payments/my');
      return res.data;
    });
  }

  // ─── AI ────────────────────────────────────────────────────────────────────

  async valuateProperty(propertyId: number): Promise<{ valuation: any }> {
    return withRetry(async () => {
      const res = await this.client.get<{ valuation: any }>(`/api/ai/valuate/${propertyId}`);
      return res.data;
    });
  }

  async getMarketInsights(city: string, listingType?: string): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get<any>('/api/ai/market', {
        params: { city, listing_type: listingType },
      });
      return res.data;
    });
  }

  // ─── Admin ─────────────────────────────────────────────────────────────────

  async getAdminStats(): Promise<AdminStats> {
    const res = await this.client.get<AdminStats>('/api/admin/stats');
    return res.data;
  }

  async getAllUsers(skip = 0, limit = 50, role?: string, search?: string): Promise<{ items: User[]; total: number }> {
    const res = await this.client.get<{ items: User[]; total: number }>('/api/admin/users', {
      params: { skip, limit, role, search },
    });
    return res.data;
  }

  async changeUserRole(userId: number, role: string): Promise<{ message: string }> {
    const res = await this.client.put<{ message: string }>(`/api/admin/users/${userId}/role`, null, {
      params: { role },
    });
    return res.data;
  }

  async toggleUserActive(userId: number): Promise<{ message: string; is_active: boolean }> {
    const res = await this.client.put<{ message: string; is_active: boolean }>(`/api/admin/users/${userId}/toggle-active`);
    return res.data;
  }

  async getAdminProperties(skip = 0, limit = 50, status?: string): Promise<{ items: any[]; total: number }> {
    const res = await this.client.get('/api/admin/properties', { params: { skip, limit, status } });
    return res.data;
  }

  async setPropertyStatus(propertyId: number, status: string): Promise<{ message: string }> {
    const res = await this.client.put(`/api/admin/properties/${propertyId}/status`, null, {
      params: { status },
    });
    return res.data;
  }

  async getPendingVerifications(limit = 20): Promise<any[]> {
    const res = await this.client.get('/api/admin/verifications/pending', { params: { limit } });
    return res.data;
  }

  async reviewVerification(verificationId: number, status: string, notes?: string): Promise<{ message: string }> {
    const res = await this.client.put(`/api/admin/verifications/${verificationId}/review`, null, {
      params: { status, notes },
    });
    return res.data;
  }

  async deleteUser(userId: number): Promise<{ message: string }> {
    const res = await this.client.delete(`/api/admin/users/${userId}`);
    return res.data;
  }

  async getAdminPayments(skip = 0, limit = 50, status?: string): Promise<{ items: any[]; total: number }> {
    const res = await this.client.get('/api/admin/payments', { params: { skip, limit, status } });
    return res.data;
  }

  async refundPayment(paymentId: number): Promise<{ message: string }> {
    const res = await this.client.post(`/api/admin/payments/${paymentId}/refund`);
    return res.data;
  }

  async getAuditLogs(skip = 0, limit = 100, userId?: number, action?: string): Promise<{ items: any[]; total: number }> {
    const res = await this.client.get('/api/admin/audit-logs', { params: { skip, limit, user_id: userId, action } });
    return res.data;
  }

  async getFraudReports(limit = 50, status?: string): Promise<{ items: any[] }> {
    const res = await this.client.get('/api/admin/fraud-reports', { params: { limit, status } });
    return res.data;
  }

  async reviewFraudReport(reportId: number, status: string, notes?: string): Promise<{ message: string }> {
    const res = await this.client.put(`/api/admin/fraud-reports/${reportId}/review`, null, {
      params: { status, notes },
    });
    return res.data;
  }

  async getPendingKYC(limit = 20): Promise<{ items: any[]; total: number }> {
    const res = await this.client.get('/api/admin/kyc/pending', { params: { limit } });
    return res.data;
  }

  async reviewKYC(kycId: number, status: string, rejectionReason?: string): Promise<{ message: string }> {
    const res = await this.client.put(`/api/admin/kyc/${kycId}/review`, null, {
      params: { status, rejection_reason: rejectionReason },
    });
    return res.data;
  }

  // ─── Subscriptions ──────────────────────────────────────────────────────────

  async getPlans(): Promise<{ role: string; plans: any[]; current_tier: string }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/subscriptions/plans');
      return res.data;
    });
  }

  async getMySubscription(): Promise<{ subscription: any; listing_limit: number; role: string }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/subscriptions/my');
      return res.data;
    });
  }

  async subscribe(tier: string, phoneNumber: string): Promise<any> {
    const res = await this.client.post('/api/subscriptions/subscribe', null, {
      params: { tier, phone_number: phoneNumber },
    });
    return res.data;
  }

  async cancelSubscription(): Promise<any> {
    const res = await this.client.post('/api/subscriptions/cancel');
    return res.data;
  }

  async getListingFeeInfo(): Promise<{
    listings_this_month: number; listing_limit: number;
    free_listings_remaining: number; listing_fee_kes: number;
    current_tier: string; message: string;
  }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/properties/listing-fee/info');
      return res.data;
    });
  }

  async featureProperty(propertyId: number, phoneNumber: string): Promise<any> {
    const res = await this.client.post(`/api/properties/${propertyId}/feature`, null, {
      params: { phone_number: phoneNumber },
    });
    return res.data;
  }

  // ─── Reports ────────────────────────────────────────────────────────────────

  async getVerificationReport(verificationId: number): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get(`/api/reports/verification/${verificationId}`);
      return res.data;
    });
  }

  async downloadReportPdf(verificationId: number): Promise<Blob> {
    const res = await this.client.get(`/api/reports/verification/${verificationId}/pdf`, {
      responseType: 'blob',
    });
    return res.data;
  }

  // ─── Enterprise API ──────────────────────────────────────────────────────────

  async createApiKey(name: string, scopes?: string, rateLimit?: number): Promise<any> {
    const res = await this.client.post('/api/enterprise/keys', null, {
      params: { name, scopes, rate_limit: rateLimit },
    });
    return res.data;
  }

  async listApiKeys(): Promise<{ keys: any[] }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/enterprise/keys');
      return res.data;
    });
  }

  async revokeApiKey(keyId: number): Promise<any> {
    const res = await this.client.delete(`/api/enterprise/keys/${keyId}`);
    return res.data;
  }

  async getApiKeyUsage(days?: number): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get('/api/enterprise/usage', { params: { days } });
      return res.data;
    });
  }

  async createWebhook(url: string, events?: string): Promise<any> {
    const res = await this.client.post('/api/enterprise/webhooks', null, {
      params: { url, events },
    });
    return res.data;
  }

  async listWebhooks(): Promise<{ webhooks: any[] }> {
    const res = await this.client.get('/api/enterprise/webhooks');
    return res.data;
  }

  // ─── Disputes ────────────────────────────────────────────────────────────────

  async getDisputes(limit = 50, status?: string): Promise<{ items: any[] }> {
    const res = await this.client.get('/api/admin/disputes', { params: { limit, status } });
    return res.data;
  }

  async resolveDispute(disputeId: number, resolution: string): Promise<any> {
    const res = await this.client.put(`/api/admin/disputes/${disputeId}/resolve`, null, {
      params: { resolution },
    });
    return res.data;
  }

  // ─── Monitoring ──────────────────────────────────────────────────────────

  async getFullHealth(): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get('/api/monitoring/health/full');
      return res.data;
    });
  }

  async getServicesStatus(): Promise<any> {
    const res = await this.client.get('/api/monitoring/health/services');
    return res.data;
  }

  async getResourceMetrics(): Promise<any> {
    const res = await this.client.get('/api/monitoring/health/resources');
    return res.data;
  }

  async getDatabaseMetrics(): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get('/api/monitoring/health/database');
      return res.data;
    });
  }

  async getRedisMetrics(): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get('/api/monitoring/health/redis');
      return res.data;
    });
  }

  // ─── Escrow ────────────────────────────────────────────────────────────────

  async createEscrow(data: {
    property_id: number; amount_kes: number; seller_id: number;
    agent_id?: number; deposit_amount_kes?: number; terms?: string;
  }): Promise<any> {
    const res = await this.client.post('/api/escrow', null, { params: data });
    return res.data;
  }

  async getMyEscrows(limit = 20): Promise<{ items: any[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ items: any[] }>('/api/escrow/my', { params: { limit } });
      return res.data;
    });
  }

  async getEscrow(escrowId: number): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get<any>(`/api/escrow/${escrowId}`);
      return res.data;
    });
  }

  // ─── Disputes ──────────────────────────────────────────────────────────────

  async fileDispute(data: {
    category: string; description: string; property_id?: number;
    subject_type?: string; subject_id?: number; evidence_urls?: string;
  }): Promise<any> {
    const res = await this.client.post('/api/disputes', null, { params: data });
    return res.data;
  }

  async getDisputeCategories(): Promise<{ categories: string[] }> {
    const res = await this.client.get<{ categories: string[] }>('/api/disputes/categories');
    return res.data;
  }

  async getMyDisputes(limit = 50): Promise<{ items: any[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ items: any[] }>('/api/disputes/my', { params: { limit } });
      return res.data;
    });
  }

  async getDispute(disputeId: number): Promise<any> {
    const res = await this.client.get<any>(`/api/disputes/${disputeId}`);
    return res.data;
  }

  // ─── Reviews ───────────────────────────────────────────────────────────────

  async writeReview(data: {
    subject_id: number; rating: number; title?: string;
    body?: string; property_id?: number;
  }): Promise<any> {
    const res = await this.client.post('/api/reviews', null, { params: data });
    return res.data;
  }

  async getSubjectReviews(subjectId: number, limit = 20): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get<any>(`/api/reviews/subject/${subjectId}`, { params: { limit } });
      return res.data;
    });
  }

  async getMyReviews(limit = 20): Promise<{ items: any[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ items: any[] }>('/api/reviews/my', { params: { limit } });
      return res.data;
    });
  }

  async getPropertyReviewStats(propertyId: number): Promise<any> {
    const res = await this.client.get<any>(`/api/reviews/property/${propertyId}`);
    return res.data;
  }

  async getTopAgents(limit = 10, minReviews = 3): Promise<any> {
    const res = await this.client.get<any>('/api/reviews/top-agents', { params: { limit, min_reviews: minReviews } });
    return res.data;
  }

  // ─── Payouts ───────────────────────────────────────────────────────────────

  async requestPayout(amountKes: number, payoutType = 'commission', description?: string): Promise<any> {
    const res = await this.client.post('/api/payouts/request', null, {
      params: { amount_kes: amountKes, payout_type: payoutType, description },
    });
    return res.data;
  }

  async getMyPayouts(limit = 50): Promise<{ items: any[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ items: any[] }>('/api/payouts/my', { params: { limit } });
      return res.data;
    });
  }

  // ─── KYC ───────────────────────────────────────────────────────────────────

  async getKycStatus(): Promise<any> {
    return withRetry(async () => {
      const res = await this.client.get('/api/kyc/status');
      return res.data;
    });
  }

  async submitKyc(formData: FormData): Promise<any> {
    const res = await this.client.post('/api/kyc/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  }

  // ─── Coupons ────────────────────────────────────────────────────────────────

  async validateCoupon(code: string): Promise<any> {
    const res = await this.client.get('/api/admin/coupons/validate', { params: { code } });
    return res.data;
  }
}

export const api = new VestraAPIClient();
export default api;
