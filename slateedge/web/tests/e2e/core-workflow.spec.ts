import { test, expect } from '@playwright/test';

// Exercises the golden path against the seeded demo account: sign in, land on
// the dashboard with the demo slate active, review the player pool, generate
// a single model-ranked lineup, and confirm it shows up in Portfolio Review.
// Requires the app to be running against a migrated + seeded database and a
// reachable optimizer-service (see README "Run the tests" section).

const DEMO_EMAIL = 'demo@slateedge.local';
const DEMO_PASSWORD = 'DemoPassword123!';

test.describe('SlateEdge core workflow', () => {
  test('sign in, browse the demo slate, and generate a lineup', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(DEMO_EMAIL);
    await page.getByLabel('Password').fill(DEMO_PASSWORD);
    await page.getByRole('button', { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByText('Demo Sunday Main Slate', { exact: false }).last()).toBeVisible();
    await expect(page.getByText('Demo Data', { exact: false }).last()).toBeVisible();

    await page.getByRole('link', { name: 'Player Pool' }).click();
    await expect(page).toHaveURL(/\/players/);
    await expect(page.getByText('Demo Player QB1')).toBeVisible();

    await page.getByRole('link', { name: 'Lineup Builder' }).click();
    await expect(page).toHaveURL(/\/lineups/);
    await page.getByLabel('Number of lineups (1-150)').fill('1');
    await page.getByRole('button', { name: /generate model-ranked lineups/i }).click();

    await expect(page.getByText(/model-ranked lineup/i)).toBeVisible({ timeout: 20_000 });

    await page.getByRole('link', { name: 'Portfolio Review' }).click();
    await expect(page).toHaveURL(/\/portfolio/);
    await expect(page.getByRole('heading', { name: /Lineups \(/ })).toBeVisible();
  });

  test('footer always shows the responsible-play notice', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(DEMO_EMAIL);
    await page.getByLabel('Password').fill(DEMO_PASSWORD);
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByText(/DFS involves financial risk/i)).toBeVisible();
  });
});
