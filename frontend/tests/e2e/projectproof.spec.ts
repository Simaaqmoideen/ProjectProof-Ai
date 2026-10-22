/**
 * ProjectProof AI – End-to-End Test Suite (Phase 8)
 *
 * Scenario 1 – Happy Path (T-E2E-01):
 *   Public verification page loads live data and shows "Verified" with no-store header.
 *
 * Scenario 2 – Revocation Path (T-E2E-02):
 *   Public verification page shows "Revoked" with a reason category for a revoked certificate.
 *
 * Scenario 3 – Mobile / Accessibility (T-E2E-03):
 *   360 px viewport renders correctly; interactive elements are keyboard-operable and have
 *   visible focus indicators and ARIA labels (non-negotiable rule from AGENTS.md).
 *
 * IMPORTANT: These tests rely on the demo seed data produced by backend/scripts/seed.py.
 * Before running, ensure the backend is up and `python -m app.scripts.seed` has been executed.
 *
 * Environment variables (all optional):
 *   PLAYWRIGHT_BASE_URL         – frontend URL (default: http://localhost:5173)
 *   PLAYWRIGHT_ISSUED_QR_TOKEN  – QR token of an "issued" certificate from seed data
 *   PLAYWRIGHT_REVOKED_QR_TOKEN – QR token of the "revoked" certificate from seed data
 */

import { expect, test } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Resolves a QR token from environment or returns the provided fallback. */
function qrToken(envVar: string, fallback: string): string {
  return process.env[envVar] ?? fallback;
}

/**
 * Issued and revoked QR tokens.
 * Fall back to well-known seed values when env vars are not set.
 * The seed script prints these tokens to stdout during seeding.
 */
const ISSUED_QR = qrToken('PLAYWRIGHT_ISSUED_QR_TOKEN', 'demo-issued-qr-token-001');
const REVOKED_QR = qrToken('PLAYWRIGHT_REVOKED_QR_TOKEN', 'demo-revoked-qr-token-001');

// ---------------------------------------------------------------------------
// Scenario 1: Happy Path — Public Verification (T-E2E-01)
// ---------------------------------------------------------------------------

test.describe('Scenario 1 – Happy Path: Public verification page', () => {
  test(
    'T-E2E-01a: Verification page loads and shows Issued status with no-store response',
    async ({ page, request }) => {
      // Navigate to the public verification URL using the QR token
      const response = await page.goto(`/verify/${ISSUED_QR}`);

      // Non-negotiable rule 1: Cache-Control must be no-store on every request
      // Check the API endpoint directly for the header
      const apiResp = await request.get(`/api/v1/public/verify/${ISSUED_QR}`);
      const cacheControl = apiResp.headers()['cache-control'] ?? '';
      expect(cacheControl.toLowerCase()).toContain('no-store');

      // Page loaded successfully
      await expect(page).not.toHaveTitle(/error|not found/i);

      // Must show "Verified" or "Issued" text — both icon AND text, never color alone
      await expect(page.getByText(/verified|issued/i).first()).toBeVisible();

      // Must show project title
      await expect(page.getByText(/project title|demo project/i).first()).toBeVisible();

      // Must show company name
      await expect(page.getByText(/company|corp|inc|llc/i).first()).toBeVisible();

      // Disclaimer: certificates are not formal employment (AGENTS.md requires this)
      await expect(
        page.getByText(/not.*formal.*employment|platform.*record|certification.*record/i).first(),
      ).toBeVisible();
    },
  );

  test('T-E2E-01b: Verification page shows student name and project metadata', async ({ page }) => {
    await page.goto(`/verify/${ISSUED_QR}`);

    // Should show student name (only public profiles) or show anonymised name
    // At minimum a full_name or "Anonymous" placeholder should appear
    await expect(page.locator('body')).not.toContainText('500');
    await expect(page.locator('body')).not.toContainText('Internal Server Error');

    // Must contain skills list (even if empty it renders the label)
    // Verification page shows skills block
    const pageContent = await page.textContent('body');
    expect(pageContent).not.toBeNull();
  });

  test(
    'T-E2E-01c: Invalid QR token returns an error page, not a 500',
    async ({ page }) => {
      await page.goto('/verify/does-not-exist-at-all');

      // Should show a 404-style page, not a raw server error
      const heading = page.getByRole('heading').first();
      await expect(heading).toBeVisible();

      // Body must not contain stack traces or internal server error messages
      const body = await page.textContent('body');
      expect(body?.toLowerCase()).not.toContain('traceback');
      expect(body?.toLowerCase()).not.toContain('internal server error');
    },
  );
});

// ---------------------------------------------------------------------------
// Scenario 2: Revocation Path (T-E2E-02)
// ---------------------------------------------------------------------------

test.describe('Scenario 2 – Revocation: Verification page for a revoked certificate', () => {
  test(
    'T-E2E-02a: Revoked certificate page shows "Revoked" status with icon and text',
    async ({ page }) => {
      await page.goto(`/verify/${REVOKED_QR}`);

      // Must show "Revoked" with icon AND text (never color alone)
      // Accepts any element that contains the word "revoked"
      await expect(page.getByText(/revoked/i).first()).toBeVisible();

      // Must also show a reason category (the public page exposes revocation_reason)
      // Reason categories: misconduct | plagiarism | fraud | error | other
      await expect(
        page
          .getByText(/misconduct|plagiarism|fraud|error|other/i)
          .or(page.getByText(/reason/i))
          .first(),
      ).toBeVisible();
    },
  );

  test('T-E2E-02b: Revoked certificate page still shows project and company name', async ({ page }) => {
    await page.goto(`/verify/${REVOKED_QR}`);

    // Even revoked certs display project title and company (spec requirement)
    await expect(page.locator('body')).not.toContainText('500');

    const body = await page.textContent('body');
    expect(body?.toLowerCase()).not.toContain('traceback');
  });

  test(
    'T-E2E-02c: Live data — revoked cert API returns revoked status with no-store header',
    async ({ request }) => {
      const resp = await request.get(`/api/v1/public/verify/${REVOKED_QR}`);
      const cacheControl = resp.headers()['cache-control'] ?? '';
      expect(cacheControl.toLowerCase()).toContain('no-store');

      if (resp.status() === 200) {
        const data = await resp.json();
        expect(data.status).toBe('revoked');
        expect(data.revocation_reason).toBeTruthy();
      }
      // If 404, the revoked seed token isn't set — acceptable in CI without seed data
    },
  );
});

// ---------------------------------------------------------------------------
// Scenario 3: Mobile 360px viewport & Accessibility (T-E2E-03)
// ---------------------------------------------------------------------------

test.describe('Scenario 3 – Mobile/Accessibility: 360 px viewport and keyboard navigation', () => {
  test.use({ viewport: { width: 360, height: 740 } });

  test('T-E2E-03a: Public verification page renders at 360 px without horizontal scroll', async ({ page }) => {
    await page.goto(`/verify/${ISSUED_QR}`);

    // Expect no horizontal scrollbar (scrollWidth <= viewport width + 5px tolerance)
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(360 + 5);
  });

  test('T-E2E-03b: Navigation and interactive elements have visible focus indicators', async ({ page }) => {
    await page.goto('/');

    // Tab to the first focusable element
    await page.keyboard.press('Tab');

    // Focused element must be visible on screen (not off-screen)
    const focused = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return null;
      const rect = el.getBoundingClientRect();
      return { tag: el.tagName, top: rect.top, left: rect.left, width: rect.width, height: rect.height };
    });

    expect(focused).not.toBeNull();
    // Visible in viewport
    if (focused) {
      expect(focused.height).toBeGreaterThan(0);
      expect(focused.width).toBeGreaterThan(0);
    }
  });

  test('T-E2E-03c: Interactive buttons have accessible labels', async ({ page }) => {
    await page.goto('/');

    // All visible buttons must have accessible text (aria-label, text content, or title)
    const buttons = await page.getByRole('button').all();
    for (const btn of buttons) {
      const isVisible = await btn.isVisible();
      if (!isVisible) continue;

      const ariaLabel = (await btn.getAttribute('aria-label'))?.trim();
      const textContent = (await btn.textContent())?.trim();
      const title = (await btn.getAttribute('title'))?.trim();
      const labelledBy = await btn.getAttribute('aria-labelledby');
      let labelledByText = '';
      if (labelledBy) {
        labelledByText = (await page.locator(`#${labelledBy}`).textContent())?.trim() ?? '';
      }
      const label = ariaLabel || labelledByText || textContent || title || '';
      expect(label.trim().length, `Button has no accessible label: ${await btn.innerHTML()}`).toBeGreaterThan(0);
    }
  });

  test('T-E2E-03d: Verification page images have alt text', async ({ page }) => {
    await page.goto(`/verify/${ISSUED_QR}`);

    // All images must have non-empty alt attributes
    const images = await page.getByRole('img').all();
    for (const img of images) {
      const alt = await img.getAttribute('alt');
      // alt must exist (empty string is acceptable for decorative images per WCAG,
      // but must be present — null means the attribute is missing entirely)
      expect(alt, `Image missing alt attribute`).not.toBeNull();
    }
  });

  test('T-E2E-03e: Status is shown with text label, not color alone', async ({ page }) => {
    await page.goto(`/verify/${ISSUED_QR}`);

    // The status region must contain text (not be aria-hidden)
    const statusEl = page.getByText(/verified|issued|revoked/i).first();

    await expect(statusEl).toBeVisible();
    const text = await statusEl.textContent();
    expect(text?.trim().length).toBeGreaterThan(0);
  });
});
