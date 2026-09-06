import { test, expect } from '@playwright/test';
import path from 'node:path';
import os from 'node:os';
import fs from 'node:fs';

// Covers importing a results CSV, linking a result to a SlateEdge-generated
// lineup, and deleting a result with confirmation + undo. Uses a unique
// contest name per run and always deletes what it created so repeat runs
// don't collide or leave residue.

const DEMO_EMAIL = 'demo@slateedge.local';
const DEMO_PASSWORD = 'DemoPassword123!';

test('import results CSV, link to a lineup, and delete with confirmation', async ({ page }) => {
  const contestName = `E2E Test Contest ${Date.now()}`;

  await page.goto('/login');
  await page.getByLabel('Email').fill(DEMO_EMAIL);
  await page.getByLabel('Password').fill(DEMO_PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  // Make sure at least one lineup exists to link against.
  await page.goto('/lineups');
  await page.getByLabel('Number of lineups (1-150)').fill('1');
  await page.getByRole('button', { name: /generate model-ranked lineups/i }).click();
  await expect(page.getByText(/model-ranked lineup/i)).toBeVisible({ timeout: 20_000 });

  const csvPath = path.join(os.tmpdir(), `slateedge-results-e2e-${Date.now()}.csv`);
  fs.writeFileSync(
    csvPath,
    [
      'slate_id,contest_name,contest_type,field_size,entry_fee,number_of_entries,total_entry_fees,total_winnings,net_profit_loss,lineup_id,final_rank,lineup_points,cash_line,top_one_percent_line,notes',
      `DEMO_SLATE_1,${contestName},GPP,1000,5,1,5,0,-5,,500,120.5,130,180,`,
    ].join('\n')
  );

  try {
    await page.goto('/results');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);
    await page.getByRole('button', { name: 'Import valid rows' }).click();
    await expect(page.getByText(/Imported 1 contest results/)).toBeVisible();

    const row = page.getByRole('row', { name: new RegExp(contestName) });
    await expect(row).toBeVisible();

    // Link it to a lineup, which should unlock the stack/salary/ownership breakdowns.
    await row.locator('select').selectOption({ index: 1 });
    await expect(page.getByRole('heading', { name: 'By stack construction' })).toBeVisible();

    // Delete offers an undo window before actually removing the row.
    await row.getByRole('button', { name: 'Delete' }).click();
    await page.getByRole('button', { name: 'Delete result' }).click();
    await expect(page.getByRole('button', { name: 'Undo' })).toBeVisible();
    await page.getByRole('button', { name: 'Undo' }).click();
    await expect(row).toBeVisible();

    // Now actually delete it for real (let the undo window elapse) so the test cleans up after itself.
    await row.getByRole('button', { name: 'Delete' }).click();
    await page.getByRole('button', { name: 'Delete result' }).click();
    await expect(page.getByRole('button', { name: 'Undo' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Undo' })).toHaveCount(0, { timeout: 10_000 });
    await expect(page.getByRole('row', { name: new RegExp(contestName) })).toHaveCount(0);
  } finally {
    fs.unlinkSync(csvPath);
  }
});
