import { Page, APIRequestContext, expect } from '@playwright/test';

// ── Types ───────────────────────────────────────────────────────────────────

export interface TestUser {
  email: string;
  password: string;
  fullName: string;
  phone: string;
  role: 'tenant' | 'landlord' | 'agent';
}

export interface TestProperty {
  title: string;
  price: number;
  currency: string;
  propertyType: string;
  bedrooms: number;
  bathrooms: number;
  location: string;
  description: string;
}

// ── Default Test Users ─────────────────────────────────────────────────────

export const TEST_USER: TestUser = {
  email: 'testuser@vestra.e2e',
  password: 'Test@Vestra2026!',
  fullName: 'Test User E2E',
  phone: '+254712345678',
  role: 'tenant',
};

export const TEST_LANDLORD: TestUser = {
  email: 'landlord@vestra.e2e',
  password: 'Landlord@2026!',
  fullName: 'Test Landlord E2E',
  phone: '+254723456789',
  role: 'landlord',
};

export const TEST_AGENT: TestUser = {
  email: 'agent@vestra.e2e',
  password: 'Agent@2026!',
  fullName: 'Test Agent E2E',
  phone: '+254734567890',
  role: 'agent',
};

// ── Sample Property Data ────────────────────────────────────────────────────

export const SAMPLE_PROPERTY: TestProperty = {
  title: 'E2E Test - Modern Apartment in Westlands',
  price: 45000,
  currency: 'KES',
  propertyType: 'apartment',
  bedrooms: 2,
  bathrooms: 1,
  location: 'Westlands, Nairobi',
  description: 'A modern 2-bedroom apartment perfect for professionals. E2E test listing.',
};

// ── Auth Helpers ────────────────────────────────────────────────────────────

/**
 * Log in via the UI form. Navigates to /auth/login, fills credentials,
 * submits, and waits for the dashboard redirect.
 */
export async function loginAs(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/auth/login');
  await page.waitForSelector('input[name="email"]', { timeout: 10000 });

  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.locator('button[type="submit"]').click();

  // Wait for navigation to dashboard or for the auth token to appear
  await page.waitForURL(/\/dashboard/, { timeout: 15000 });
}

/**
 * Log in via the API directly (bypasses UI) and stores the token.
 * Useful for seeding data or setting up auth state before a test.
 */
export async function loginViaAPI(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<{ accessToken: string; refreshToken: string }> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const res = await request.post(`${baseUrl}/api/auth/login`, {
    data: { email, password },
  });

  expect(res.status()).toBe(200);

  const body = await res.json();
  return {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
  };
}

/**
 * Register a new user via the API. Returns the token response.
 */
export async function registerViaAPI(
  request: APIRequestContext,
  user: TestUser,
): Promise<{ accessToken: string; refreshToken: string }> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const res = await request.post(`${baseUrl}/api/auth/register`, {
    data: {
      email: user.email,
      password: user.password,
      full_name: user.fullName,
      phone: user.phone,
      role: user.role,
    },
  });

  // 409 means already registered — that is fine for test setup
  if (res.status() === 409) {
    return loginViaAPI(request, user.email, user.password);
  }

  expect(res.status()).toBe(201);

  const body = await res.json();
  return {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
  };
}

/**
 * Set auth token in localStorage so the page loads as an authenticated user.
 */
export async function setAuthToken(page: Page, token: string): Promise<void> {
  await page.evaluate((t) => {
    localStorage.setItem('vestra_token', t);
  }, token);
}

/**
 * Clear auth token from localStorage (log out).
 */
export async function clearAuthToken(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.removeItem('vestra_token');
    localStorage.removeItem('vestra_refresh_token');
  });
}

// ── Property Helpers ───────────────────────────────────────────────────────

/**
 * Create a test property via the API. Requires an auth token.
 * Returns the created property ID.
 */
export async function createTestProperty(
  request: APIRequestContext,
  token: string,
  overrides?: Partial<TestProperty>,
): Promise<{ id: string }> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const propertyData = { ...SAMPLE_PROPERTY, ...overrides };

  const res = await request.post(`${baseUrl}/api/properties`, {
    data: {
      title: propertyData.title,
      price: propertyData.price,
      currency: propertyData.currency,
      property_type: propertyData.propertyType,
      bedrooms: propertyData.bedrooms,
      bathrooms: propertyData.bathrooms,
      location: propertyData.location,
      description: propertyData.description,
    },
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  expect(res.status()).toBe(201);

  return res.json();
}

/**
 * Delete a test property by ID.
 */
export async function deleteTestProperty(
  request: APIRequestContext,
  token: string,
  propertyId: string,
): Promise<void> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  await request.delete(`${baseUrl}/api/properties/${propertyId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

// ── Data Seeding ────────────────────────────────────────────────────────────

export interface SeedDataResult {
  users: TestUser[];
  properties: Array<{ id: string }>;
}

/**
 * Seed the database with test users and properties.
 * Registers users via API, then creates properties for landlords.
 * Returns created user tokens and property IDs.
 */
export async function seedTestData(
  request: APIRequestContext,
  options?: {
    users?: TestUser[];
    createProperties?: boolean;
  },
): Promise<SeedDataResult> {
  const users = options?.users ?? [TEST_USER, TEST_LANDLORD, TEST_AGENT];
  const createdUsers: TestUser[] = [];
  const properties: Array<{ id: string }> = [];

  for (const user of users) {
    await registerViaAPI(request, user);
    createdUsers.push(user);
  }

  if (options?.createProperties !== false) {
    // Create properties as the landlord
    const { accessToken } = await loginViaAPI(request, TEST_LANDLORD.email, TEST_LANDLORD.password);

    const prop1 = await createTestProperty(request, accessToken, {
      title: 'E2E Test - Luxury Villa in Karen',
      price: 120000,
      propertyType: 'villa',
      bedrooms: 4,
      bathrooms: 3,
      location: 'Karen, Nairobi',
    });
    properties.push(prop1);

    const prop2 = await createTestProperty(request, accessToken, {
      title: 'E2E Test - Studio in Kilimani',
      price: 25000,
      propertyType: 'studio',
      bedrooms: 1,
      bathrooms: 1,
      location: 'Kilimani, Nairobi',
    });
    properties.push(prop2);
  }

  return { users: createdUsers, properties };
}

/**
 * Clean up all test data by deleting properties created during seeding.
 */
export async function cleanupTestData(
  request: APIRequestContext,
  data: SeedDataResult,
): Promise<void> {
  const { accessToken } = await loginViaAPI(request, TEST_LANDLORD.email, TEST_LANDLORD.password);

  for (const prop of data.properties) {
    await deleteTestProperty(request, accessToken, prop.id);
  }
}

// ── Misc Helpers ───────────────────────────────────────────────────────────

/**
 * Generate a unique email for test isolation.
 */
export function uniqueEmail(prefix = 'e2e'): string {
  const ts = Date.now();
  const rand = Math.random().toString(36).substring(2, 8);
  return `${prefix}-${ts}-${rand}@vestra.e2e`;
}

/**
 * Wait for a toast/notification to appear and then dismiss.
 */
export async function waitAndDismissToast(page: Page, timeout = 5000): Promise<void> {
  const toast = page.locator('[data-testid="toast"], [role="alert"], .Toast, .toast').first();
  await toast.waitFor({ state: 'visible', timeout }).catch(() => {});
  // Dismiss if it has a close button
  const closeBtn = toast.locator('button, [aria-label="Close"]').first();
  if (await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.click();
  }
}
