import { test, expect } from '@playwright/test';

// Covers the second-pass gap-fill features added after the initial build:
// configurable roster slots, per-player exposure overrides, saveable custom
// presets, regenerating a single lineup in place, and undo-on-delete. Runs
// against the same seeded demo account as core-workflow.spec.ts.

const DEMO_EMAIL = 'demo@slateedge.local';
const DEMO_PASSWORD = 'DemoPassword123!';

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(DEMO_EMAIL);
  await page.getByLabel('Password').fill(DEMO_PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

test.describe('SlateEdge gap-fill features', () => {
  test('roster construction is editable and a custom preset can be saved and reapplied', async ({ page }) => {
    await login(page);
    await page.goto('/lineups');

    // Roster editor: 9 default slots rendered as selects, each removable.
    const slotSelects = page.locator('select').filter({ hasText: 'QB' });
    await expect(page.getByText('9 roster spots total.')).toBeVisible();

    // Add a slot, bringing the roster to 10.
    await page.getByRole('button', { name: '+ Add slot' }).click();
    await expect(page.getByText('10 roster spots total.')).toBeVisible();

    // Set a per-player exposure override.
    await page.getByRole('heading', { name: 'Diversification & exposure' }).scrollIntoViewIfNeeded();
    await page.locator('#exposure-override-player').selectOption({ index: 1 });
    await page.locator('#exposure-override-max').fill('50');
    await page.getByRole('button', { name: 'Add override' }).click();
    await expect(page.getByText(/max 50%/)).toBeVisible();

    // Save the current settings as a named preset.
    await page.getByRole('button', { name: 'Save current settings as preset' }).click();
    await page.getByLabel('Preset name').fill('E2E Test Preset');
    await page.getByRole('button', { name: 'Save preset', exact: true }).click();
    await expect(page.getByText(/Saved preset "E2E Test Preset"/)).toBeVisible();
    await page.getByRole('button', { name: 'Close' }).click();

    // Reload to confirm it persisted server-side, then apply it back.
    await page.reload();
    await expect(page.getByRole('button', { name: 'E2E Test Preset', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'E2E Test Preset', exact: true }).click();
    await expect(page.getByText('Using preset: E2E Test Preset')).toBeVisible();
  });

  test('regenerating a single lineup keeps other lineups and delete offers undo', async ({ page }) => {
    await login(page);
    await page.goto('/lineups');
    await page.getByLabel('Number of lineups (1-150)').fill('2');
    await page.getByRole('button', { name: /generate model-ranked lineups/i }).click();
    await expect(page.getByText(/model-ranked lineup/i)).toBeVisible({ timeout: 20_000 });

    await page.getByRole('link', { name: 'Portfolio Review' }).click();
    await expect(page).toHaveURL(/\/portfolio/);

    const rowCountBefore = await page.locator('tbody tr').count();
    await page.getByRole('button', { name: 'Regenerate' }).first().click();
    await expect(page.locator('tbody tr')).toHaveCount(rowCountBefore, { timeout: 20_000 });

    // Delete shows an undo bar rather than deleting immediately.
    await page.getByRole('button', { name: 'Delete' }).first().click();
    await expect(page.getByRole('button', { name: 'Undo' })).toBeVisible();
    await page.getByRole('button', { name: 'Undo' }).click();
    await expect(page.getByRole('button', { name: 'Undo' })).toHaveCount(0);
  });
});
