import { test, expect } from "@playwright/test";

test.describe("Authentication Flow", () => {
  test("landing page loads", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Vestra/i);
  });

  test("login page renders", async ({ page }) => {
    await page.goto("/auth/login");
    await expect(page.locator("text=Welcome back").or(page.locator("text=Sign in"))).toBeVisible();
  });

  test("register page renders", async ({ page }) => {
    await page.goto("/auth/register");
    await expect(page.locator("text=Create").or(page.locator("text=Register"))).toBeVisible();
  });

  test("navigation to market works without auth", async ({ page }) => {
    await page.goto("/");
    // Try to navigate to market
    const marketLink = page.locator('a[href*="market"]').first();
    if (await marketLink.isVisible()) {
      await marketLink.click();
      await expect(page).toHaveURL(/market/);
    }
  });

  test("protected pages redirect to login", async ({ page }) => {
    await page.goto("/dashboard");
    // Should redirect to login or show auth guard
    await expect(page.locator("text=Login").or(page.locator("text=Sign in"))).toBeVisible();
  });

  test("forgot password page renders", async ({ page }) => {
    await page.goto("/auth/forgot-password");
    await expect(page.locator("text=Forgot").or(page.locator("text=Reset"))).toBeVisible();
  });

  test("verify page accessible without auth", async ({ page }) => {
    await page.goto("/verify");
    await expect(page).not.toHaveURL(/error/);
  });

  test("properties page loads", async ({ page }) => {
    await page.goto("/market");
    // Should show property listings or empty state
    await expect(page.locator("text=Properties").or(page.locator("text=property"))).toBeVisible();
  });

  test("admin login page works", async ({ page }) => {
    await page.goto("/admin/login");
    await expect(page.locator("input")).toBeVisible();
  });
});
