import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('login page renders', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('text=Sign In').first()).toBeVisible();
  });

  test('redirects to login when not authenticated', async ({ page }) => {
    await page.goto('/board');
    // Should redirect to login since not authenticated
    await expect(page).toHaveURL(/login/);
  });

  test('login page has email and password fields', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input#email')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('login page shows project title', async ({ page }) => {
    await page.goto('/login');
    await expect(
      page.locator('text=PCT — Project Construction Tool'),
    ).toBeVisible();
  });

  test('login button is present', async ({ page }) => {
    await page.goto('/login');
    await expect(
      page.locator('button:has-text("Sign In / Register")'),
    ).toBeVisible();
  });
});
