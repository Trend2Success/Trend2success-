'use server';

import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';
import { parseAndValidate, RowError } from '@/lib/csv/engine';
import { SALARY_COLUMNS, salaryRowSchema } from '@/lib/csv/salary';
import { PROJECTION_COLUMNS, projectionRowSchema } from '@/lib/csv/projection';
import { RESULTS_COLUMNS, resultsRowSchema } from '@/lib/csv/results';
import { deriveGameId, recomputeSlateAnalytics } from '@/lib/server/analytics';

export interface ImportFormState {
  error?: string;
  success?: string;
  totalRows?: number;
  validCount?: number;
  duplicatesRemoved?: number;
  errors?: RowError[];
  unmatchedRequired?: string[];
  unrecognizedHeaders?: string[];
  committed?: boolean;
}

async function readFile(formData: FormData): Promise<string | null> {
  const file = formData.get('file');
  if (!(file instanceof File) || file.size === 0) return null;
  return file.text();
}

// ---------------------------------------------------------------------------
// Salary CSV (creates/updates the Slate + Player roster for a slate)
// ---------------------------------------------------------------------------
export async function previewSalaryCsvAction(_prev: ImportFormState, formData: FormData): Promise<ImportFormState> {
  await requireUser();
  const text = await readFile(formData);
  if (!text) return { error: 'Choose a CSV file first.' };

  const result = parseAndValidate(text, SALARY_COLUMNS, salaryRowSchema, {
    dedupeKey: (r) => r.player_id,
  });

  if (result.unmatchedRequired.length > 0) {
    return {
      error: `Missing required columns: ${result.unmatchedRequired.join(', ')}`,
      unmatchedRequired: result.unmatchedRequired,
      unrecognizedHeaders: result.unrecognizedHeaders,
    };
  }

  const distinctSlateIds = new Set(result.validRows.map((r) => r.slate_id));
  const extraErrors: RowError[] = [];
  if (distinctSlateIds.size > 1) {
    extraErrors.push({
      rowNumber: 0,
      messages: [`File contains ${distinctSlateIds.size} different slate_id values — upload one slate per file.`],
      raw: {},
    });
  }

  return {
    totalRows: result.totalRows,
    validCount: result.validRows.length,
    duplicatesRemoved: result.duplicatesRemoved,
    errors: [...extraErrors, ...result.errors].slice(0, 200),
    unrecognizedHeaders: result.unrecognizedHeaders,
    success: `Parsed ${result.totalRows} rows: ${result.validRows.length} valid, ${result.errors.length} with errors, ${result.duplicatesRemoved} duplicate player IDs removed.`,
  };
}

export async function commitSalaryCsvAction(_prev: ImportFormState, formData: FormData): Promise<ImportFormState> {
  const user = await requireUser();
  const text = await readFile(formData);
  if (!text) return { error: 'Choose a CSV file first.' };

  const result = parseAndValidate(text, SALARY_COLUMNS, salaryRowSchema, {
    dedupeKey: (r) => r.player_id,
  });

  if (result.unmatchedRequired.length > 0 || result.validRows.length === 0) {
    return { error: 'No valid rows to import. Check column mapping and row errors first.' };
  }

  const distinctSlateIds = new Set(result.validRows.map((r) => r.slate_id));
  if (distinctSlateIds.size > 1) {
    return { error: 'File contains multiple slate_id values. Upload one slate per file.' };
  }

  const first = result.validRows[0]!;
  const slate = await prisma.slate.upsert({
    where: { userId_slateId: { userId: user.id, slateId: first.slate_id } },
    update: { slateName: first.slate_name, sport: first.sport, contestDate: new Date(first.contest_date) },
    create: {
      userId: user.id,
      slateId: first.slate_id,
      slateName: first.slate_name,
      sport: first.sport,
      contestDate: new Date(first.contest_date),
    },
  });

  await prisma.$transaction(
    result.validRows.map((row) =>
      prisma.player.upsert({
        where: { slateId_playerId: { slateId: slate.id, playerId: row.player_id } },
        update: {
          playerName: row.player_name,
          team: row.team,
          opponent: row.opponent,
          position: row.position,
          rosterPositions: row.roster_positions || row.position,
          salary: row.salary,
          gameInfo: row.game_info,
          gameId: deriveGameId(row.team, row.opponent),
          startTime: row.start_time ? new Date(row.start_time) : null,
          status: row.status,
        },
        create: {
          slateId: slate.id,
          playerId: row.player_id,
          playerName: row.player_name,
          team: row.team,
          opponent: row.opponent,
          position: row.position,
          rosterPositions: row.roster_positions || row.position,
          salary: row.salary,
          gameInfo: row.game_info,
          gameId: deriveGameId(row.team, row.opponent),
          startTime: row.start_time ? new Date(row.start_time) : null,
          status: row.status,
        },
      })
    )
  );

  await prisma.importBatch.create({
    data: {
      slateId: slate.id,
      kind: 'salary',
      sourceLabel: 'User Upload',
      fileName: (formData.get('file') as File)?.name,
      rowCount: result.validRows.length,
      errorCount: result.errors.length,
    },
  });

  await logAudit(
    user.id,
    'import.salary',
    { rows: result.validRows.length, errors: result.errors.length, duplicatesRemoved: result.duplicatesRemoved },
    { type: 'Slate', id: slate.id }
  );

  revalidatePath('/slates');
  revalidatePath('/players');
  revalidatePath('/dashboard');

  return {
    committed: true,
    validCount: result.validRows.length,
    totalRows: result.totalRows,
    duplicatesRemoved: result.duplicatesRemoved,
    errors: result.errors.slice(0, 200),
    success: `Imported ${result.validRows.length} players into "${slate.slateName}".`,
  };
}

// ---------------------------------------------------------------------------
// Projection CSV (attaches to the currently active slate)
// ---------------------------------------------------------------------------
export async function previewProjectionCsvAction(_prev: ImportFormState, formData: FormData): Promise<ImportFormState> {
  await requireUser();
  const text = await readFile(formData);
  if (!text) return { error: 'Choose a CSV file first.' };

  const result = parseAndValidate(text, PROJECTION_COLUMNS, projectionRowSchema, {
    dedupeKey: (r) => r.player_id,
  });

  if (result.unmatchedRequired.length > 0) {
    return { error: `Missing required columns: ${result.unmatchedRequired.join(', ')}`, unmatchedRequired: result.unmatchedRequired };
  }

  return {
    totalRows: result.totalRows,
    validCount: result.validRows.length,
    duplicatesRemoved: result.duplicatesRemoved,
    errors: result.errors.slice(0, 200),
    unrecognizedHeaders: result.unrecognizedHeaders,
    success: `Parsed ${result.totalRows} rows: ${result.validRows.length} valid, ${result.errors.length} with errors.`,
  };
}

export async function commitProjectionCsvAction(_prev: ImportFormState, formData: FormData): Promise<ImportFormState> {
  const user = await requireUser();
  const slateId = String(formData.get('slateId') ?? '');
  const sourceLabel = String(formData.get('sourceLabel') || 'User Upload');
  const text = await readFile(formData);
  if (!text) return { error: 'Choose a CSV file first.' };
  if (!slateId) return { error: 'Select an active slate before importing projections.' };

  const slate = await prisma.slate.findFirst({ where: { id: slateId, userId: user.id } });
  if (!slate) return { error: 'Slate not found.' };

  const result = parseAndValidate(text, PROJECTION_COLUMNS, projectionRowSchema, {
    dedupeKey: (r) => r.player_id,
  });

  if (result.unmatchedRequired.length > 0 || result.validRows.length === 0) {
    return { error: 'No valid rows to import. Check column mapping and row errors first.' };
  }

  const source = await prisma.projectionSource.upsert({
    where: { slateId_sourceLabel: { slateId: slate.id, sourceLabel } },
    update: {},
    create: { slateId: slate.id, sourceLabel },
  });

  await prisma.$transaction(
    result.validRows.map((row) =>
      prisma.projectionRow.upsert({
        where: { sourceId_playerId: { sourceId: source.id, playerId: row.player_id } },
        update: {
          playerName: row.player_name,
          projectedPoints: row.projected_points,
          floor: row.floor,
          ceiling: row.ceiling,
          standardDeviation: row.standard_deviation,
          projectedOwnership: row.projected_ownership,
          expectedUsage: row.expected_minutes_or_snaps,
          targetShareOrUsage: row.target_share_or_usage,
          notes: row.notes,
          lastUpdated: row.last_updated ? new Date(row.last_updated) : null,
        },
        create: {
          sourceId: source.id,
          playerId: row.player_id,
          playerName: row.player_name,
          projectedPoints: row.projected_points,
          floor: row.floor,
          ceiling: row.ceiling,
          standardDeviation: row.standard_deviation,
          projectedOwnership: row.projected_ownership,
          expectedUsage: row.expected_minutes_or_snaps,
          targetShareOrUsage: row.target_share_or_usage,
          notes: row.notes,
          lastUpdated: row.last_updated ? new Date(row.last_updated) : null,
        },
      })
    )
  );

  await recomputeProjectionSnapshotsFromSources(slate.id, user.id);

  await prisma.importBatch.create({
    data: {
      slateId: slate.id,
      kind: 'projection',
      sourceLabel,
      fileName: (formData.get('file') as File)?.name,
      rowCount: result.validRows.length,
      errorCount: result.errors.length,
    },
  });

  await logAudit(
    user.id,
    'import.projection',
    { rows: result.validRows.length, errors: result.errors.length, sourceLabel },
    { type: 'Slate', id: slate.id }
  );

  revalidatePath('/players');
  revalidatePath('/projections');
  revalidatePath('/ownership');
  revalidatePath('/dashboard');

  return {
    committed: true,
    validCount: result.validRows.length,
    totalRows: result.totalRows,
    errors: result.errors.slice(0, 200),
    success: `Imported ${result.validRows.length} projection rows from "${sourceLabel}".`,
  };
}

/**
 * Rebuilds each player's ProjectionSnapshot as an equal-weighted blend across
 * all projection sources imported for the slate. This is the default
 * behavior; the Projection Lab lets the user set custom per-source weights,
 * which calls the same recompute with explicit weights and resets any
 * previously-applied manual point/percent adjustments (documented in the UI).
 */
export async function recomputeProjectionSnapshotsFromSources(
  slateId: string,
  userId: string,
  weightsBySourceId?: Record<string, number>
) {
  const sources = await prisma.projectionSource.findMany({
    where: { slateId },
    include: { rows: true },
  });

  const byPlayer = new Map<string, { playerName: string; rows: { sourceId: string; row: (typeof sources)[number]['rows'][number] }[] }>();
  for (const source of sources) {
    for (const row of source.rows) {
      const entry = byPlayer.get(row.playerId) ?? { playerName: row.playerName, rows: [] };
      entry.rows.push({ sourceId: source.id, row });
      byPlayer.set(row.playerId, entry);
    }
  }

  const players = await prisma.player.findMany({ where: { slateId } });
  const playerByExternalId = new Map(players.map((p) => [p.playerId, p]));

  const ops = [];
  for (const [externalId, entry] of byPlayer.entries()) {
    const player = playerByExternalId.get(externalId);
    if (!player) continue;

    const weightedRows = entry.rows.map(({ sourceId, row }) => ({
      points: row.projectedPoints,
      weight: weightsBySourceId?.[sourceId] ?? 1,
    }));
    const totalWeight = weightedRows.reduce((s, r) => s + r.weight, 0) || 1;
    const basePoints =
      Math.round(
        (weightedRows.reduce((s, r) => s + r.points * r.weight, 0) / totalWeight) * 100
      ) / 100;

    const avg = (values: (number | null)[]) => {
      const present = values.filter((v): v is number => v !== null);
      if (present.length === 0) return null;
      return Math.round((present.reduce((a, b) => a + b, 0) / present.length) * 100) / 100;
    };

    const floor = avg(entry.rows.map((r) => r.row.floor));
    const ceiling = avg(entry.rows.map((r) => r.row.ceiling));
    const stdev = avg(entry.rows.map((r) => r.row.standardDeviation));
    const ownership = avg(entry.rows.map((r) => r.row.projectedOwnership));

    ops.push(
      prisma.projectionSnapshot.upsert({
        where: { playerId: player.id },
        update: {
          basePoints,
          finalPoints: basePoints,
          floor,
          ceiling: ceiling ?? basePoints,
          standardDeviation: stdev,
          projectedOwnership: ownership,
        },
        create: {
          playerId: player.id,
          basePoints,
          finalPoints: basePoints,
          floor,
          ceiling: ceiling ?? basePoints,
          standardDeviation: stdev,
          projectedOwnership: ownership,
        },
      })
    );
  }

  if (ops.length > 0) {
    await prisma.$transaction(ops);
  }
  await recomputeSlateAnalytics(slateId, userId);
}

// ---------------------------------------------------------------------------
// Results CSV
// ---------------------------------------------------------------------------
export async function previewResultsCsvAction(_prev: ImportFormState, formData: FormData): Promise<ImportFormState> {
  await requireUser();
  const text = await readFile(formData);
  if (!text) return { error: 'Choose a CSV file first.' };

  const result = parseAndValidate(text, RESULTS_COLUMNS, resultsRowSchema);
  if (result.unmatchedRequired.length > 0) {
    return { error: `Missing required columns: ${result.unmatchedRequired.join(', ')}`, unmatchedRequired: result.unmatchedRequired };
  }

  return {
    totalRows: result.totalRows,
    validCount: result.validRows.length,
    errors: result.errors.slice(0, 200),
    success: `Parsed ${result.totalRows} rows: ${result.validRows.length} valid, ${result.errors.length} with errors.`,
  };
}

export async function commitResultsCsvAction(_prev: ImportFormState, formData: FormData): Promise<ImportFormState> {
  const user = await requireUser();
  const text = await readFile(formData);
  if (!text) return { error: 'Choose a CSV file first.' };

  const result = parseAndValidate(text, RESULTS_COLUMNS, resultsRowSchema);
  if (result.unmatchedRequired.length > 0 || result.validRows.length === 0) {
    return { error: 'No valid rows to import. Check column mapping and row errors first.' };
  }

  const slates = await prisma.slate.findMany({ where: { userId: user.id } });
  const slateByExternalId = new Map(slates.map((s) => [s.slateId, s]));

  const unknownSlateErrors: RowError[] = [];
  const creates = [];
  for (const [idx, row] of result.validRows.entries()) {
    const slate = slateByExternalId.get(row.slate_id);
    if (!slate) {
      unknownSlateErrors.push({
        rowNumber: idx + 2,
        messages: [`slate_id "${row.slate_id}" does not match any imported slate — import its salary CSV first.`],
        raw: {},
      });
      continue;
    }
    creates.push(
      prisma.contestResult.create({
        data: {
          slateId: slate.id,
          contestName: row.contest_name,
          contestType: row.contest_type,
          fieldSize: row.field_size,
          entryFeeCents: Math.round(row.entry_fee * 100),
          numberOfEntries: row.number_of_entries,
          totalEntryFeesCents: Math.round((row.total_entry_fees ?? row.entry_fee * row.number_of_entries) * 100),
          totalWinningsCents: Math.round((row.total_winnings ?? 0) * 100),
          netProfitLossCents: Math.round(
            (row.net_profit_loss ?? (row.total_winnings ?? 0) - (row.total_entry_fees ?? row.entry_fee * row.number_of_entries)) * 100
          ),
          externalLineupRef: row.lineup_id || null,
          finalRank: row.final_rank,
          lineupPoints: row.lineup_points,
          cashLine: row.cash_line,
          topOnePercentLine: row.top_one_percent_line,
          notes: row.notes,
        },
      })
    );
  }

  if (creates.length > 0) {
    await prisma.$transaction(creates);
  }

  await logAudit(user.id, 'import.results', { imported: creates.length, skipped: unknownSlateErrors.length });

  revalidatePath('/results');
  revalidatePath('/dashboard');

  return {
    committed: true,
    validCount: creates.length,
    totalRows: result.totalRows,
    errors: [...unknownSlateErrors, ...result.errors].slice(0, 200),
    success: `Imported ${creates.length} contest results.`,
  };
}
