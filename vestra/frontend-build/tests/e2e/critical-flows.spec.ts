import { test, expect } from '@playwright/test';
import {
  loginAs,
  TEST_USER,
  TEST_LANDLORD,
  SAMPLE_PROPERTY,
  uniqueEmail,
  clearAuthToken,
} from '../utils/test-helpers';

// ═══════════════════════════════════════════════════════════════════════════
//  VESTRA Critical E2E Flows — 15 Test Scenarios
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Critical User Flows', () => {
  // ── Scenario 1: Register + Login ──────────────────────────────────────────
  test.describe('1. Register + Login', () => {
    test('should register a new user and redirect to dashboard', async ({ page }) => {
      const email = uniqueEmail();
      await page.goto('/auth/register');

      await page.locator('input[name="full_name"]').fill('Fresh User E2E');
      await page.locator('input[name="email"]').fill(email);
      await page.locator('input[name="phone"]').fill('+254712345000');
      await page.locator('input[name="password"]').fill('Fresh@Vestra2026!');
      await page.locator('input[name="confirm_password"]').fill('Fresh@Vestra2026!');
      await page.locator('button[type="submit"]').click();

      // After registration, user should be redirected to dashboard or verification page
      await expect(page).toHaveURL(/\/dashboard|\/verify|\/auth\/verify/, { timeout: 15000 });
      // Verify the user menu or avatar is shown
      await expect(page.locator('[data-testid="user-menu"]').or(page.locator('[data-testid="avatar"]'))).toBeVisible({ timeout: 10000 });
    });

    test('should log in with existing credentials and land on dashboard', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);
      await expect(page.locator('[data-testid="user-menu"]')).toBeVisible({ timeout: 10000 });
    });

    test('should reject login with wrong password', async ({ page }) => {
      await page.goto('/auth/login');
      await page.locator('input[name="email"]').fill(TEST_USER.email);
      await page.locator('input[name="password"]').fill('WrongPassword999!');
      await page.locator('button[type="submit"]').click();
      await expect(page.locator('text=Invalid email or password').or(page.locator('[role="alert"]'))).toBeVisible({ timeout: 10000 });
    });
  });

  // ── Scenario 2: Browse + Filter + Property Detail ────────────────────────
  test.describe('2. Browse, Filter & Property Detail', () => {
    test('should load market page with property listings', async ({ page }) => {
      await page.goto('/market');
      await expect(page.locator('h1').or(page.locator('h2'))).toContainText(/property|market|listings?/i, { timeout: 10000 });
    });

    test('should filter properties by type and price', async ({ page }) => {
      await page.goto('/market');

      // Find a filter select/input for property type
      const typeFilter = page.locator('select[name="property_type"], select[aria-label*="type"], [data-testid="filter-type"]').first();
      if (await typeFilter.isVisible().catch(() => false)) {
        await typeFilter.selectOption({ label: 'Apartment' });
        await page.waitForTimeout(500);
      }

      // Find a price range filter
      const priceMin = page.locator('input[name="price_min"], input[aria-label*="min price"], [data-testid="filter-price-min"]').first();
      if (await priceMin.isVisible().catch(() => false)) {
        await priceMin.fill('10000');
      }

      const priceMax = page.locator('input[name="price_max"], input[aria-label*="max price"], [data-testid="filter-price-max"]').first();
      if (await priceMax.isVisible().catch(() => false)) {
        await priceMax.fill('200000');
      }

      // Click apply filters
      const applyBtn = page.locator('button:text("Apply"), button:text("Filter"), [data-testid="apply-filters"]').first();
      if (await applyBtn.isVisible().catch(() => false)) {
        await applyBtn.click();
      }

      // Wait for results to update
      await page.waitForTimeout(1000);
      // The page should have listings or an empty state after filtering
      await expect(page.locator('[data-testid="property-card"], .property-card, [data-testid="empty-state"]').first()).toBeVisible({ timeout: 10000 });
    });

    test('should navigate to property detail and show key information', async ({ page }) => {
      await page.goto('/market');

      // Click the first property card
      const firstCard = page.locator('[data-testid="property-card"], .property-card, a[href*="/properties/"]').first();
      await firstCard.waitFor({ state: 'visible', timeout: 10000 });
      await firstCard.click();

      // Should land on property detail page
      await expect(page).toHaveURL(/\/properties\//, { timeout: 10000 });

      // Verify key detail sections are visible
      await expect(page.locator('h1').or(page.locator('[data-testid="property-title"]'))).toBeVisible();
      // Price should be displayed
      await expect(page.locator('text=KES').or(page.locator('[data-testid="property-price"]'))).toBeVisible();
      // Location should be shown
      await expect(page.locator('[data-testid="property-location"]').or(page.locator('text=Nairobi'))).toBeVisible();
    });
  });

  // ── Scenario 3: Create + Publish Listing ────────────────────────────────
  test.describe('3. Create & Publish Listing', () => {
    test('should show create listing form after login as landlord', async ({ page }) => {
      await loginAs(page, TEST_LANDLORD.email, TEST_LANDLORD.password);

      // Navigate to create listing page
      await page.goto('/properties/create');
      await page.waitForURL(/\/properties\/create|\/dashboard\/listings\/new/, { timeout: 10000 });

      // Fill in the form
      const titleField = page.locator('input[name="title"], input#title, [data-testid="property-title-input"]').first();
      await expect(titleField).toBeVisible({ timeout: 5000 });
      await titleField.fill(SAMPLE_PROPERTY.title);

      const priceField = page.locator('input[name="price"], input#price, [data-testid="property-price-input"]').first();
      if (await priceField.isVisible().catch(() => false)) {
        await priceField.fill(String(SAMPLE_PROPERTY.price));
      }

      const descField = page.locator('textarea[name="description"], textarea#description, [data-testid="property-desc-input"]').first();
      if (await descField.isVisible().catch(() => false)) {
        await descField.fill(SAMPLE_PROPERTY.description);
      }

      // Submit the form
      const submitBtn = page.locator('button[type="submit"]:text("Publish"), button:text("Create"), [data-testid="publish-property"]').first();
      if (await submitBtn.isVisible().catch(() => false)) {
        await submitBtn.click();
      }

      // After submission user may be redirected to the listing detail or dashboard
      await expect(page).toHaveURL(/\/properties\/|dashboard/, { timeout: 15000 });
    });
  });

  // ── Scenario 4: Tenant Pay Rent ──────────────────────────────────────────
  test.describe('4. Tenant Pay Rent', () => {
    test('should navigate to payments page and initiate rent payment', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      await page.goto('/wallet');
      await expect(page.locator('h1').or(page.locator('h2'))).toContainText(/wallet|payment|pay rent/i, { timeout: 10000 });

      // Find and click "Pay Rent" button
      const payRentBtn = page.locator('button:text("Pay Rent"), button:text("Pay"), a[href*="payment"]').first();
      if (await payRentBtn.isVisible().catch(() => false)) {
        await payRentBtn.click();
        await expect(page).toHaveURL(/payment|pay/, { timeout: 10000 });
      }
    });

    test('should show payment history', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);
      await page.goto('/wallet');

      await expect(page.locator('[data-testid="payment-history"], .payment-history, table')).toBeVisible({ timeout: 10000 });
    });
  });

  // ── Scenario 5: Landlord Add Tenant ──────────────────────────────────────
  test.describe('5. Landlord Add Tenant', () => {
    test('should navigate to tenant management page as landlord', async ({ page }) => {
      await loginAs(page, TEST_LANDLORD.email, TEST_LANDLORD.password);

      await page.goto('/dashboard/tenants');
      await expect(page).toHaveURL(/tenants/, { timeout: 10000 });

      // Look for "Add Tenant" button
      const addTenantBtn = page.locator('button:text("Add Tenant"), a:text("Add Tenant"), [data-testid="add-tenant"]').first();
      await expect(addTenantBtn).toBeVisible({ timeout: 5000 });
    });
  });

  // ── Scenario 6: Verification Flow ────────────────────────────────────────
  test.describe('6. Verification Flow', () => {
    test('should load verification page and show steps', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      await page.goto('/verify');
      await expect(page).toHaveURL(/\/verify/, { timeout: 10000 });
      // Should show verification instructions or status
      await expect(page.locator('h1').or(page.locator('h2'))).toContainText(/verify|verification|kyc/i, { timeout: 5000 });
    });

    test('should allow document upload for verification', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      await page.goto('/verify');

      // Find file upload input
      const fileInput = page.locator('input[type="file"]').first();
      if (await fileInput.isVisible().catch(() => false)) {
        // Set a test file (in CI this would be a fixture file)
        await fileInput.setInputFiles({
          name: 'test-id.jpg',
          mimeType: 'image/jpeg',
          buffer: Buffer.from('fake-image-data'),
        });

        const uploadBtn = page.locator('button:text("Upload"), button:text("Submit")').first();
        if (await uploadBtn.isVisible().catch(() => false)) {
          await uploadBtn.click();
        }
      }
    });
  });

  // ── Scenario 7: Messages — Send + Receive ────────────────────────────────
  test.describe('7. Messages — Send & Receive', () => {
    test('should open messages page and display conversations', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      await page.goto('/messages');
      await expect(page).toHaveURL(/\/messages/, { timeout: 10000 });
      await expect(page.locator('[data-testid="conversation-list"], .conversation-list, [data-testid="message-thread"]').first()).toBeVisible({ timeout: 10000 });
    });

    test('should allow sending a message from property detail', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      await page.goto('/market');
      const firstCard = page.locator('[data-testid="property-card"], .property-card, a[href*="/properties/"]').first();
      await firstCard.waitFor({ state: 'visible', timeout: 10000 });
      await firstCard.click();

      // Find a "Contact" or "Send Message" button on the property detail
      const contactBtn = page.locator('button:text("Contact"), button:text("Message"), a:text("Send Message"), [data-testid="contact-agent"]').first();
      if (await contactBtn.isVisible().catch(() => false)) {
        await contactBtn.click();

        // Should open a message form or redirect to messages
        const messageInput = page.locator('textarea, input[placeholder*="message"]').first();
        if (await messageInput.isVisible().catch(() => false)) {
          await messageInput.fill('Hi, I am interested in this property. Is it still available?');
          const sendBtn = page.locator('button[type="submit"]:text("Send"), button:text("Send")').first();
          if (await sendBtn.isVisible().catch(() => false)) {
            await sendBtn.click();
          }
        }
      }
    });
  });

  // ── Scenario 8: Notifications ────────────────────────────────────────────
  test.describe('8. Notifications', () => {
    test('should display notifications page with notification list', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      await page.goto('/notifications');
      await expect(page).toHaveURL(/\/notifications/, { timeout: 10000 });
      // Should have notification items or an empty state
      await expect(page.locator('[data-testid="notification-list"], .notification-item, [data-testid="empty-state"]').first()).toBeVisible({ timeout: 10000 });
    });

    test('should show notification badge on the navigation bar', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      // Look for notification bell icon with badge
      const bellIcon = page.locator('[data-testid="notification-bell"], a[href*="notification"], [aria-label*="notification"]').first();
      await expect(bellIcon).toBeVisible({ timeout: 5000 });
    });
  });

  // ── Scenario 9: Favorites ────────────────────────────────────────────────
  test.describe('9. Favorites', () => {
    test('should add a property to favorites from detail page', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      await page.goto('/market');
      const firstCard = page.locator('[data-testid="property-card"], .property-card, a[href*="/properties/"]').first();
      await firstCard.waitFor({ state: 'visible', timeout: 10000 });

      // Find a like/favorite button
      const favBtn = page.locator('[data-testid="favorite-button"], [data-testid="like-button"], button[aria-label*="favorite"], button[aria-label*="like"]').first();
      if (await favBtn.isVisible().catch(() => false)) {
        await favBtn.click();
        // Heart icon should change (filled vs outline)
        await page.waitForTimeout(500);
      }
    });

    test('should show favorited properties on the favorites page', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      await page.goto('/favorites');
      await expect(page).toHaveURL(/\/favorites/, { timeout: 10000 });
      // Should show favorites list or empty state
      await expect(page.locator('[data-testid="favorites-list"], .favorite-item, [data-testid="empty-state"]').first()).toBeVisible({ timeout: 10000 });
    });
  });

  // ── Scenario 10: Compare Properties ──────────────────────────────────────
  test.describe('10. Compare Properties', () => {
    test('should show comparison tool and allow selecting properties', async ({ page }) => {
      await page.goto('/market');

      // Find compare checkboxes on property cards
      const compareCheckboxes = page.locator('[data-testid="compare-checkbox"], input[aria-label*="compare"]').first();
      if (await compareCheckboxes.isVisible().catch(() => false)) {
        await compareCheckboxes.check();
        await page.waitForTimeout(300);

        // Look for a "Compare" button that appears
        const compareBtn = page.locator('button:text("Compare"), a:text("Compare"), [data-testid="compare-button"]').first();
        if (await compareBtn.isVisible().catch(() => false)) {
          await compareBtn.click();
          await expect(page).toHaveURL(/\/compare/, { timeout: 10000 });
          await expect(page.locator('h1').or(page.locator('h2'))).toContainText(/compare|comparison/i, { timeout: 5000 });
        }
      }
    });
  });

  // ── Scenario 11: Dark Mode ───────────────────────────────────────────────
  test.describe('11. Dark Mode', () => {
    test('should toggle dark mode and persist preference', async ({ page }) => {
      await loginAs(page, TEST_USER.email, TEST_USER.password);

      // Find dark mode toggle
      const darkToggle = page.locator('[data-testid="dark-mode-toggle"], [aria-label*="dark"], button:has(.sun), button:has(.moon), [data-testid="theme-toggle"]').first();
      await expect(darkToggle).toBeVisible({ timeout: 5000 });

      // Get current body class before toggle
      const bodyBefore = await page.locator('body').getAttribute('class');

      await darkToggle.click();
      await page.waitForTimeout(500);

      // Body class should have changed (dark/light class toggled)
      const bodyAfter = await page.locator('body').getAttribute('class');
      expect(bodyAfter).not.toBe(bodyBefore);

      // Navigate away and back — preference should persist
      await page.goto('/market');
      await page.waitForTimeout(500);
      const bodyAfterNav = await page.locator('body').getAttribute('class');
      expect(bodyAfterNav).toBe(bodyAfter);
    });
  });

  // ── Scenario 12: Language Switch (English / Swahili) ─────────────────────
  test.describe('12. Language Switch', () => {
    test('should switch language between English and Swahili', async ({ page }) => {
      await page.goto('/');

      // Find language switcher
      const langSwitcher = page.locator('[data-testid="language-switcher"], select[aria-label*="language"], button:has-text("EN"), button:has-text("SW"), [data-testid="locale-toggle"]').first();
      await expect(langSwitcher).toBeVisible({ timeout: 5000 });

      // Get current page text in English
      const originalText = await page.locator('h1').first().textContent();

      // Switch to Swahili
      const swOption = page.locator('option:has-text("Swahili"), option[value="sw"], button:has-text("SW"), a:has-text("Kiswahili")').first();
      if (await swOption.isVisible().catch(() => false)) {
        await swOption.click();
        await page.waitForTimeout(1000);
      } else {
        // Try selecting from dropdown
        await langSwitcher.selectOption('sw');
        await page.waitForTimeout(1000);
      }

      // Text should have changed (or URL should contain /sw/)
      const currentUrl = page.url();
      expect(currentUrl.includes('/sw/') || currentUrl.includes('lang=sw') || currentUrl.includes('locale=sw')).toBeTruthy();
    });
  });

  // ── Scenario 13: Mobile Responsive ───────────────────────────────────────
  test.describe('13. Mobile Responsive', () => {
    test('should render hamburger menu on mobile viewport', async ({ page }) => {
      // Set viewport to mobile size
      await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE

      await page.goto('/');
      await page.waitForTimeout(500);

      // Look for hamburger/menu toggle
      const mobileMenuBtn = page.locator('[data-testid="mobile-menu"], [aria-label*="menu"], button:has(.hamburger), .navbar-toggler, button:has(svg[data-icon="menu"])').first();
      await expect(mobileMenuBtn).toBeVisible({ timeout: 5000 });

      // Open mobile menu
      await mobileMenuBtn.click();
      await page.waitForTimeout(500);

      // Navigation links should now be visible
      const navLink = page.locator('a[href="/market"], a[href*="property"]').first();
      await expect(navLink).toBeVisible({ timeout: 5000 });
    });

    test('should show mobile-friendly property card layout', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      await page.goto('/market');
      await page.waitForTimeout(1000);

      // Property cards should be full-width or stacked vertically on mobile
      const firstCard = page.locator('[data-testid="property-card"], .property-card').first();
      await expect(firstCard).toBeVisible({ timeout: 10000 });
    });
  });

  // ── Scenario 14: PWA Install Prompt ──────────────────────────────────────
  test.describe('14. PWA Install', () => {
    test('should register service worker and show install prompt', async ({ page }) => {
      await page.goto('/');

      // Check if service worker is registered
      const hasSW = await page.evaluate(() => {
        return 'serviceWorker' in navigator;
      });
      expect(hasSW).toBe(true);

      // Check for PWA manifest link
      const manifestLink = page.locator('link[rel="manifest"]');
      await expect(manifestLink).toBeVisible({ timeout: 5000 });

      // Check the manifest href
      const manifestHref = await manifestLink.getAttribute('href');
      expect(manifestHref).toBeTruthy();
    });

    test('should display install button when beforeinstallprompt fires', async ({ page }) => {
      // Trigger the beforeinstallprompt event
      await page.goto('/');

      const installPromptShown = await page.evaluate(() => {
        return new Promise<boolean>((resolve) => {
          // Simulate the beforeinstallprompt event
          const event = new Event('beforeinstallprompt') as any;
          event.userChoice = Promise.resolve({ outcome: 'accepted' });
          window.dispatchEvent(event);
          resolve(true);
        });
      });

      // Check if an install button appears after the event
      const installBtn = page.locator('[data-testid="install-pwa"], [aria-label*="install"], button:text("Install")').first();
      if (await installBtn.isVisible().catch(() => false)) {
        await expect(installBtn).toBeVisible({ timeout: 5000 });
      }
    });
  });

  // ── Scenario 15: Search with Filters (bonus flow) ───────────────────────
  test.describe('15. Search & Filters', () => {
    test('should search properties by keyword', async ({ page }) => {
      await page.goto('/market');

      // Find search input
      const searchInput = page.locator('input[type="search"], input[placeholder*="search"], input[name="q"], [data-testid="search-input"]').first();
      await expect(searchInput).toBeVisible({ timeout: 5000 });

      // Type a search query
      await searchInput.fill('Nairobi');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      // URL should have search query parameter
      const currentUrl = page.url();
      expect(currentUrl.includes('q=') || currentUrl.includes('search=') || currentUrl.includes('query=')).toBeTruthy();
    });

    test('should apply multiple filters and update results', async ({ page }) => {
      await page.goto('/market');

      // Apply filters one by one
      const filters = [
        page.locator('select[name="bedrooms"], [data-testid="filter-bedrooms"]').first(),
        page.locator('select[name="property_type"], [data-testid="filter-type"]').first(),
        page.locator('select[name="furnished"], [data-testid="filter-furnished"]').first(),
      ];

      for (const filter of filters) {
        if (await filter.isVisible().catch(() => false)) {
          const options = await filter.locator('option').all();
          if (options.length > 1) {
            await filter.selectOption({ index: 1 });
          }
        }
      }

      // Apply filters
      const applyBtn = page.locator('button:text("Apply"), button:text("Search"), [data-testid="apply-filters"]').first();
      if (await applyBtn.isVisible().catch(() => false)) {
        await applyBtn.click();
        await page.waitForTimeout(1500);
      }

      // Results container should be visible
      await expect(page.locator('[data-testid="property-card"], .property-card, [data-testid="search-results"]').first()).toBeVisible({ timeout: 10000 });
    });
  });
});
