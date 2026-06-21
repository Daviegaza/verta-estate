import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

// Augment Axios types to support custom retry flag
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

import { getCookie } from '@/lib/utils';
import type {
  AuthToken, User, Property, PropertyListResponse,
  PropertyCreate, Verification, Payment, AdminStats,
  PropertySearch, AISearchResult,
  VestimaEstimate, VestimaHistoryEntry,
  EscrowTransaction, Dispute, Review, SubjectReviews, Payout,
  KYCVerification, SubscriptionPlan, UserSubscription,
  APIKeyInfo, WebhookInfo,
} from '@/types';

// In development, use relative URLs so Next.js rewrites proxy to the backend.
// In production/staging, also use relative URLs (nginx handles the proxying).
// The NEXT_PUBLIC_API_URL is only needed for server-side requests or direct debugging.
const BASE_URL = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
const isDev = process.env.NODE_ENV !== 'production';
const MAX_RETRIES = isDev ? 1 : 2;       // Dev: 1 retry. Prod: 2 retries.
const RETRY_DELAY_MS = isDev ? 300 : 800; // Dev: 300ms. Prod: 800ms.

// ── Retry helper ──────────────────────────────────────────────────────────────

function shouldRetry(error: AxiosError, attempt: number): boolean {
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
      // Fast retry — just a short pause
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
      return withRetry(fn, attempt + 1);
    }
    throw err;
  }
}

// ── API Client ────────────────────────────────────────────────────────────────

class VestraAPIClient {
  client: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (token: string) => void;
    reject: (error: unknown) => void;
  }> = [];

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: isDev ? 10000 : 30000,  // Dev: 10s max. Prod: 30s.
      headers: { 'Content-Type': 'application/json' },
    });

    // Attach token, correlation ID, and CSRF token
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
        // Add CSRF token for state-changing requests
        const method = (config.method || 'get').toUpperCase();
        if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
          const csrfToken = getCookie('vestra_csrf');
          if (csrfToken) {
            config.headers['X-CSRF-Token'] = csrfToken;
          }
        }
      }
      return config;
    });

    // Response interceptor — handles expired tokens gracefully with refresh
    // Amazon-style: never force-redirect on public pages. Just clear stale tokens
    // and let individual page guards handle auth requirements.
    // Also handles automatic refresh token rotation on 401.
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status !== 401) {
          return Promise.reject(error);
        }

        const originalRequest = error.config as InternalAxiosRequestConfig;

        // Don't retry the refresh endpoint itself
        if (originalRequest.url?.includes('/api/auth/refresh')) {
          // Clear auth and redirect
          this.clearAuthAndRedirect(originalRequest);
          return Promise.reject(error);
        }

        // If already refreshing, queue this request
        if (this.isRefreshing) {
          return new Promise<string>((resolve, reject) => {
            this.failedQueue.push({ resolve, reject });
          }).then((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.client(originalRequest);
          });
        }

        // Prevent infinite retry loops
        if (originalRequest._retry) {
          this.clearAuthAndRedirect(originalRequest);
          return Promise.reject(error);
        }

        originalRequest._retry = true;
        this.isRefreshing = true;

        const refreshToken =
          typeof window !== 'undefined'
            ? localStorage.getItem('vestra_refresh_token')
            : null;

        if (!refreshToken) {
          // No refresh token available — fall through to original 401 handling
          this.isRefreshing = false;
          this.clearAuthAndRedirect(originalRequest);
          return Promise.reject(error);
        }

        // Attempt to refresh the token
        return api
          .refreshToken(refreshToken)
          .then((data) => {
            // Store new tokens
            localStorage.setItem('vestra_token', data.access_token);
            localStorage.setItem('vestra_refresh_token', data.refresh_token);

            // Process any queued requests with the new token
            this.processQueue(null, data.access_token);

            // Retry the original request with the new token
            originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
            return this.client(originalRequest);
          })
          .catch((refreshError) => {
            // Refresh failed — reject all queued requests and force logout
            this.processQueue(refreshError, null);
            this.clearAuthAndRedirect(originalRequest);
            return Promise.reject(refreshError);
          })
          .finally(() => {
            this.isRefreshing = false;
          });
      }
    );
  }

  private processQueue(error: unknown, token: string | null = null): void {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else if (token) {
        resolve(token);
      }
    });
    this.failedQueue = [];
  }

  private clearAuthAndRedirect(_originalRequest?: InternalAxiosRequestConfig): void {
    if (typeof window === 'undefined') return;

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
    localStorage.removeItem('vestra_refresh_token');
    localStorage.removeItem('vestra_user');

    // Only redirect if AuthGuard would have required login anyway
    if (isAuthRequiredPath) {
      window.location.href = '/auth/login?redirect=' + encodeURIComponent(path);
    }
    // On public pages: just clear token, stay on page, let user browse freely
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

  async refreshToken(refreshToken: string): Promise<{
    access_token: string; refresh_token: string; token_type: string;
  }> {
    const res = await this.client.post('/api/auth/refresh', {
      refresh_token: refreshToken,
    });
    return res.data;
  }

  async logout(): Promise<{ message: string }> {
    const res = await this.client.post('/api/auth/logout');
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

  async aiSuggestions(query: string): Promise<{ query: string; suggestions: Array<{ text: string; type: string }> }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/ai/suggestions', {
        params: { q: query },
      });
      return res.data;
    });
  }

  async aiPropertyInsights(propertyId: number): Promise<Record<string, unknown>> {
    return withRetry(async () => {
      const res = await this.client.get<Record<string, unknown>>(`/api/ai/insights/${propertyId}`);
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
      const res = await this.client.get<{ items: Property[]; total: number }>('/api/properties/my');
      // Backend returns { items: [...], total: N } — unwrap if needed
      const data = res.data;
      if (data && Array.isArray(data.items)) return data.items;
      return [];
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

  async valuateProperty(propertyId: number): Promise<{ valuation: Record<string, unknown> }> {
    return withRetry(async () => {
      const res = await this.client.get<{ valuation: Record<string, unknown> }>(`/api/ai/valuate/${propertyId}`);
      return res.data;
    });
  }

  async getMarketInsights(city: string, listingType?: string): Promise<Record<string, unknown>> {
    return withRetry(async () => {
      const res = await this.client.get<Record<string, unknown>>('/api/ai/market', {
        params: { city, listing_type: listingType },
      });
      return res.data;
    });
  }

  async getVestimaEstimate(propertyId: number): Promise<{ property_id: number; vestima: VestimaEstimate }> {
    return withRetry(async () => {
      const res = await this.client.get<{ property_id: number; vestima: VestimaEstimate }>(`/api/ai/vestima/${propertyId}`);
      return res.data;
    });
  }

  async getVestimaCustomEstimate(data: Record<string, unknown>): Promise<{ vestima: VestimaEstimate }> {
    return withRetry(async () => {
      const res = await this.client.post<{ vestima: VestimaEstimate }>('/api/ai/vestima/custom', data);
      return res.data;
    });
  }

  async getVestimaHistory(propertyId: number, limit = 5): Promise<{ property_id: number; history: VestimaHistoryEntry[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ property_id: number; history: VestimaHistoryEntry[] }>(`/api/ai/vestima/history/${propertyId}`, {
        params: { limit },
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

  async getAdminProperties(skip = 0, limit = 50, status?: string): Promise<{ items: Property[]; total: number }> {
    const res = await this.client.get<{ items: Property[]; total: number }>('/api/admin/properties', { params: { skip, limit, status } });
    return res.data;
  }

  async setPropertyStatus(propertyId: number, status: string): Promise<{ message: string }> {
    const res = await this.client.put<{ message: string }>(`/api/admin/properties/${propertyId}/status`, null, {
      params: { status },
    });
    return res.data;
  }

  async getPendingVerifications(limit = 20): Promise<Verification[]> {
    const res = await this.client.get<Verification[]>('/api/admin/verifications/pending', { params: { limit } });
    return res.data;
  }

  async reviewVerification(verificationId: number, status: string, notes?: string): Promise<{ message: string }> {
    const res = await this.client.put<{ message: string }>(`/api/admin/verifications/${verificationId}/review`, null, {
      params: { status, notes },
    });
    return res.data;
  }

  async deleteUser(userId: number): Promise<{ message: string }> {
    const res = await this.client.delete<{ message: string }>(`/api/admin/users/${userId}`);
    return res.data;
  }

  async getAdminPayments(skip = 0, limit = 50, status?: string): Promise<{ items: Payment[]; total: number }> {
    const res = await this.client.get<{ items: Payment[]; total: number }>('/api/admin/payments', { params: { skip, limit, status } });
    return res.data;
  }

  async refundPayment(paymentId: number): Promise<{ message: string }> {
    const res = await this.client.post<{ message: string }>(`/api/admin/payments/${paymentId}/refund`);
    return res.data;
  }

  async getAuditLogs(skip = 0, limit = 100, userId?: number, action?: string): Promise<{ items: Record<string, unknown>[]; total: number }> {
    const res = await this.client.get<{ items: Record<string, unknown>[]; total: number }>('/api/admin/audit-logs', { params: { skip, limit, user_id: userId, action } });
    return res.data;
  }

  async getFraudReports(limit = 50, status?: string): Promise<{ items: Record<string, unknown>[] }> {
    const res = await this.client.get<{ items: Record<string, unknown>[] }>('/api/admin/fraud-reports', { params: { limit, status } });
    return res.data;
  }

  async reviewFraudReport(reportId: number, status: string, notes?: string): Promise<{ message: string }> {
    const res = await this.client.put<{ message: string }>(`/api/admin/fraud-reports/${reportId}/review`, null, {
      params: { status, notes },
    });
    return res.data;
  }

  async getPendingKYC(limit = 20): Promise<{ items: KYCVerification[]; total: number }> {
    const res = await this.client.get<{ items: KYCVerification[]; total: number }>('/api/admin/kyc/pending', { params: { limit } });
    return res.data;
  }

  async reviewKYC(kycId: number, status: string, rejectionReason?: string): Promise<{ message: string }> {
    const res = await this.client.put<{ message: string }>(`/api/admin/kyc/${kycId}/review`, null, {
      params: { status, rejection_reason: rejectionReason },
    });
    return res.data;
  }

  // ─── Subscriptions ──────────────────────────────────────────────────────────

  async getPlans(): Promise<{ role: string; plans: SubscriptionPlan[]; current_tier: string }> {
    return withRetry(async () => {
      const res = await this.client.get<{ role: string; plans: SubscriptionPlan[]; current_tier: string }>('/api/subscriptions/plans');
      return res.data;
    });
  }

  async getMySubscription(): Promise<{ subscription: UserSubscription; listing_limit: number; role: string }> {
    return withRetry(async () => {
      const res = await this.client.get<{ subscription: UserSubscription; listing_limit: number; role: string }>('/api/subscriptions/my');
      return res.data;
    });
  }

  async subscribe(tier: string, phoneNumber: string): Promise<Record<string, unknown>> {
    const res = await this.client.post<Record<string, unknown>>('/api/subscriptions/subscribe', null, {
      params: { tier, phone_number: phoneNumber },
    });
    return res.data;
  }

  async cancelSubscription(): Promise<Record<string, unknown>> {
    const res = await this.client.post<Record<string, unknown>>('/api/subscriptions/cancel');
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

  async featureProperty(propertyId: number, phoneNumber: string): Promise<Record<string, unknown>> {
    const res = await this.client.post<Record<string, unknown>>(`/api/properties/${propertyId}/feature`, null, {
      params: { phone_number: phoneNumber },
    });
    return res.data;
  }

  // ─── Reports ────────────────────────────────────────────────────────────────

  async getVerificationReport(verificationId: number): Promise<Record<string, unknown>> {
    return withRetry(async () => {
      const res = await this.client.get<Record<string, unknown>>(`/api/reports/verification/${verificationId}`);
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

  async createApiKey(name: string, scopes?: string, rateLimit?: number): Promise<APIKeyInfo> {
    const res = await this.client.post<APIKeyInfo>('/api/enterprise/keys', null, {
      params: { name, scopes, rate_limit: rateLimit },
    });
    return res.data;
  }

  async listApiKeys(): Promise<{ keys: APIKeyInfo[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ keys: APIKeyInfo[] }>('/api/enterprise/keys');
      return res.data;
    });
  }

  async revokeApiKey(keyId: number): Promise<{ message: string }> {
    const res = await this.client.delete<{ message: string }>(`/api/enterprise/keys/${keyId}`);
    return res.data;
  }

  async getApiKeyUsage(days?: number): Promise<Record<string, unknown>> {
    return withRetry(async () => {
      const res = await this.client.get<Record<string, unknown>>('/api/enterprise/usage', { params: { days } });
      return res.data;
    });
  }

  async createWebhook(url: string, events?: string): Promise<WebhookInfo> {
    const res = await this.client.post<WebhookInfo>('/api/enterprise/webhooks', null, {
      params: { url, events },
    });
    return res.data;
  }

  async listWebhooks(): Promise<{ webhooks: WebhookInfo[] }> {
    const res = await this.client.get<{ webhooks: WebhookInfo[] }>('/api/enterprise/webhooks');
    return res.data;
  }

  // ─── Disputes ────────────────────────────────────────────────────────────────

  async getDisputes(limit = 50, status?: string): Promise<{ items: Dispute[] }> {
    const res = await this.client.get<{ items: Dispute[] }>('/api/admin/disputes', { params: { limit, status } });
    return res.data;
  }

  async resolveDispute(disputeId: number, resolution: string): Promise<{ message: string }> {
    const res = await this.client.put<{ message: string }>(`/api/admin/disputes/${disputeId}/resolve`, null, {
      params: { resolution },
    });
    return res.data;
  }

  // ─── Monitoring ──────────────────────────────────────────────────────────

  async getFullHealth(): Promise<Record<string, unknown>> {
    return withRetry(async () => {
      const res = await this.client.get<Record<string, unknown>>('/api/monitoring/health/full');
      return res.data;
    });
  }

  async getServicesStatus(): Promise<Record<string, unknown>> {
    const res = await this.client.get<Record<string, unknown>>('/api/monitoring/health/services');
    return res.data;
  }

  async getResourceMetrics(): Promise<Record<string, unknown>> {
    const res = await this.client.get<Record<string, unknown>>('/api/monitoring/health/resources');
    return res.data;
  }

  async getDatabaseMetrics(): Promise<Record<string, unknown>> {
    return withRetry(async () => {
      const res = await this.client.get<Record<string, unknown>>('/api/monitoring/health/database');
      return res.data;
    });
  }

  async getRedisMetrics(): Promise<Record<string, unknown>> {
    return withRetry(async () => {
      const res = await this.client.get<Record<string, unknown>>('/api/monitoring/health/redis');
      return res.data;
    });
  }

  // ─── Escrow ────────────────────────────────────────────────────────────────

  async createEscrow(data: {
    property_id: number; amount_kes: number; seller_id: number;
    agent_id?: number; deposit_amount_kes?: number; terms?: string;
  }): Promise<EscrowTransaction> {
    const res = await this.client.post<EscrowTransaction>('/api/escrow', null, { params: data });
    return res.data;
  }

  async getMyEscrows(limit = 20): Promise<{ items: EscrowTransaction[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ items: EscrowTransaction[] }>('/api/escrow/my', { params: { limit } });
      return res.data;
    });
  }

  async getEscrow(escrowId: number): Promise<EscrowTransaction> {
    return withRetry(async () => {
      const res = await this.client.get<EscrowTransaction>(`/api/escrow/${escrowId}`);
      return res.data;
    });
  }

  // ─── Disputes ──────────────────────────────────────────────────────────────

  async fileDispute(data: {
    category: string; description: string; property_id?: number;
    subject_type?: string; subject_id?: number; evidence_urls?: string;
  }): Promise<Dispute> {
    const res = await this.client.post<Dispute>('/api/disputes', null, { params: data });
    return res.data;
  }

  async getDisputeCategories(): Promise<{ categories: string[] }> {
    const res = await this.client.get<{ categories: string[] }>('/api/disputes/categories');
    return res.data;
  }

  async getMyDisputes(limit = 50): Promise<{ items: Dispute[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ items: Dispute[] }>('/api/disputes/my', { params: { limit } });
      return res.data;
    });
  }

  async getDispute(disputeId: number): Promise<Dispute> {
    const res = await this.client.get<Dispute>(`/api/disputes/${disputeId}`);
    return res.data;
  }

  // ─── Reviews ───────────────────────────────────────────────────────────────

  async writeReview(data: {
    subject_id: number; rating: number; title?: string;
    body?: string; property_id?: number;
  }): Promise<Review> {
    const res = await this.client.post<Review>('/api/reviews', null, { params: data });
    return res.data;
  }

  async getSubjectReviews(subjectId: number, limit = 20): Promise<SubjectReviews> {
    return withRetry(async () => {
      const res = await this.client.get<SubjectReviews>(`/api/reviews/subject/${subjectId}`, { params: { limit } });
      return res.data;
    });
  }

  async getMyReviews(limit = 20): Promise<{ items: Review[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ items: Review[] }>('/api/reviews/my', { params: { limit } });
      return res.data;
    });
  }

  async getPropertyReviewStats(propertyId: number): Promise<Record<string, unknown>> {
    const res = await this.client.get<Record<string, unknown>>(`/api/reviews/property/${propertyId}`);
    return res.data;
  }

  async getTopAgents(limit = 10, minReviews = 3): Promise<Record<string, unknown>> {
    const res = await this.client.get<Record<string, unknown>>('/api/reviews/top-agents', { params: { limit, min_reviews: minReviews } });
    return res.data;
  }

  // ─── Payouts ───────────────────────────────────────────────────────────────

  async requestPayout(amountKes: number, payoutType = 'commission', description?: string): Promise<Payout> {
    const res = await this.client.post<Payout>('/api/payouts/request', null, {
      params: { amount_kes: amountKes, payout_type: payoutType, description },
    });
    return res.data;
  }

  async getMyPayouts(limit = 50): Promise<{ items: Payout[] }> {
    return withRetry(async () => {
      const res = await this.client.get<{ items: Payout[] }>('/api/payouts/my', { params: { limit } });
      return res.data;
    });
  }

  // ─── KYC ───────────────────────────────────────────────────────────────────

  async getKycStatus(): Promise<KYCVerification> {
    return withRetry(async () => {
      const res = await this.client.get<KYCVerification>('/api/kyc/status');
      return res.data;
    });
  }

  async submitKyc(formData: FormData): Promise<KYCVerification> {
    const res = await this.client.post<KYCVerification>('/api/kyc/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  }

  // ─── Coupons ────────────────────────────────────────────────────────────────

  async validateCoupon(code: string): Promise<Record<string, unknown>> {
    const res = await this.client.get<Record<string, unknown>>('/api/admin/coupons/validate', { params: { code } });
    return res.data;
  }

  // ─── Notifications (v4.3.0) ─────────────────────────────────────────────────

  async getNotifications(): Promise<{ data: Array<Record<string, unknown>> }> {
    return withRetry(async () => {
      const res = await this.client.get<{ data: Array<Record<string, unknown>> }>('/api/v1/notifications/');
      return res.data;
    });
  }

  async markNotificationRead(id: number): Promise<void> {
    await this.client.put(`/api/v1/notifications/${id}/read`);
  }

  async markAllNotificationsRead(): Promise<void> {
    await this.client.put('/api/v1/notifications/read-all');
  }

  // ─── Currencies (v4.3.0) ────────────────────────────────────────────────────

  async getCurrencies(): Promise<{ base: string; currencies: Array<{ code: string; symbol: string; name: string; rate_to_kes: number; updated_at: string | null }>; last_updated: string | null }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/v1/currencies');
      return res.data;
    });
  }

  async getCurrencyRates(): Promise<{ base: string; rates: Record<string, number>; last_updated: string | null }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/v1/currencies/rates');
      return res.data;
    });
  }

  async convertCurrency(amount: number, fromCurrency: string, toCurrency: string): Promise<{ amount: number; from: string; to: string; result: number; formatted: string; rate: number }> {
    const res = await this.client.get('/api/v1/currencies/convert', {
      params: { amount, from_currency: fromCurrency, to_currency: toCurrency },
    });
    return res.data;
  }

  // ─── Investment Advisor (v4.3.0) ─────────────────────────────────────────────

  async analyzeInvestment(params: {
    price: number; city: string; area?: string; property_type?: string;
    bedrooms?: number; monthly_rent_estimate?: number;
    property_size_sqm?: number; trust_score?: number;
  }): Promise<{ success: boolean; analysis: Record<string, unknown> }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/v1/investment/analyze', { params });
      return res.data;
    });
  }

  async getMarketConditions(city: string): Promise<{ city: string; market_status: string; avg_price_per_sqm: number; avg_rental_yield: number; price_trend: string; demand_level: string; supply_level: string; days_on_market_avg: number; investor_sentiment: number }> {
    return withRetry(async () => {
      const res = await this.client.get('/api/v1/investment/market-conditions', { params: { city } });
      return res.data;
    });
  }
}

export const api = new VestraAPIClient();
export default api;
