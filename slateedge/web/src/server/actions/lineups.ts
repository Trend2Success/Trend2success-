'use server';

import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';
import { runOptimizer } from '@/lib/optimizer/client';
import {
  DEFAULT_FLEX_POSITIONS,
  DEFAULT_OBJECTIVE_WEIGHTS,
  DEFAULT_ROSTER_SLOTS,
  DEFAULT_STACK_RULES,
  GroupRule,
  OptimizeRequest,
  PlayerExposureOverride,
} from '@/lib/optimizer/types';

export interface LineupFormState {
  error?: string;
  success?: string;
  lineupsGenerated?: number;
  warnings?: string[];
}

function parseJsonArray<T>(formData: FormData, key: string, fallback: T[]): T[] {
  const raw = formData.get(key);
  if (!raw) return fallback;
  try {
    const parsed = JSON.parse(String(raw));
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : fallback;
  } catch {
    return fallback;
  }
}

function parsePerPlayerExposure(formData: FormData): PlayerExposureOverride[] {
  const raw = formData.get('perPlayerExposureJson');
  if (!raw) return [];
  try {
    const parsed = JSON.parse(String(raw));
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

type PlayerWithProjection = Awaited<ReturnType<typeof prisma.player.findMany<{ include: { projection: true } }>>>[number];

/** Builds the full optimizer request from Lineup Builder form fields plus the
 * slate's current player pool (always read fresh so locks/excludes/projection
 * edits made since a run was saved are respected on every new solve). */
function buildOptimizeRequest(formData: FormData, players: PlayerWithProjection[]): OptimizeRequest {
  const numLineups = Math.max(1, Math.min(150, Number(formData.get('numLineups') ?? 1)));
  const salaryCap = Number(formData.get('salaryCap') ?? 50000);
  const minSalary = Number(formData.get('minSalary') ?? 0);
  const maxSalary = Number(formData.get('maxSalary') ?? salaryCap);
  const minUnique = Number(formData.get('minUnique') ?? 0);
  const maxPerTeam = Number(formData.get('maxPerTeam') ?? 4);
  const minPerGame = formData.get('minPerGame') ? Number(formData.get('minPerGame')) : null;
  const maxPerGame = formData.get('maxPerGame') ? Number(formData.get('maxPerGame')) : null;
  const globalMaxOwnership = formData.get('globalMaxOwnership') ? Number(formData.get('globalMaxOwnership')) : null;
  const minTotalProjection = formData.get('minTotalProjection') ? Number(formData.get('minTotalProjection')) : null;
  const minTotalCeiling = formData.get('minTotalCeiling') ? Number(formData.get('minTotalCeiling')) : null;
  const reproducible = formData.get('reproducible') === 'true';
  const randomSeed = reproducible ? Number(formData.get('randomSeed') ?? 42) : null;

  const rosterSlots = parseJsonArray<string>(formData, 'rosterSlotsJson', DEFAULT_ROSTER_SLOTS);
  const flexPositions = parseJsonArray<string>(formData, 'flexPositionsJson', DEFAULT_FLEX_POSITIONS);

  const objectiveWeights = {
    ...DEFAULT_OBJECTIVE_WEIGHTS,
    projection: Number(formData.get('weightProjection') ?? DEFAULT_OBJECTIVE_WEIGHTS.projection),
    ceiling: Number(formData.get('weightCeiling') ?? DEFAULT_OBJECTIVE_WEIGHTS.ceiling),
    leverage: Number(formData.get('weightLeverage') ?? DEFAULT_OBJECTIVE_WEIGHTS.leverage),
    ownership_penalty: Number(formData.get('weightOwnershipPenalty') ?? DEFAULT_OBJECTIVE_WEIGHTS.ownership_penalty),
  };

  const stackRules = {
    ...DEFAULT_STACK_RULES,
    qb_stack_min: Number(formData.get('qbStackMin') ?? DEFAULT_STACK_RULES.qb_stack_min),
    qb_stack_max: Number(formData.get('qbStackMax') ?? DEFAULT_STACK_RULES.qb_stack_max),
    bring_back_min: Number(formData.get('bringBackMin') ?? DEFAULT_STACK_RULES.bring_back_min),
    allow_rb_with_qb: formData.get('allowRbWithQb') !== 'false',
    allow_dst_vs_offense: formData.get('allowDstVsOffense') === 'true',
  };

  const globalMaxExposurePct = formData.get('globalMaxExposurePct') ? Number(formData.get('globalMaxExposurePct')) : null;
  const globalMinExposurePct = formData.get('globalMinExposurePct') ? Number(formData.get('globalMinExposurePct')) : null;
  const maxExposure: Record<string, number> = {};
  const minExposure: Record<string, number> = {};
  if (globalMaxExposurePct !== null) {
    for (const p of players) maxExposure[p.playerId] = globalMaxExposurePct / 100;
  }
  if (globalMinExposurePct !== null) {
    for (const p of players) minExposure[p.playerId] = globalMinExposurePct / 100;
  }
  // Per-player overrides always win over the global default.
  for (const override of parsePerPlayerExposure(formData)) {
    if (override.max !== undefined && override.max !== null) maxExposure[override.player_id] = override.max / 100;
    if (override.min !== undefined && override.min !== null) minExposure[override.player_id] = override.min / 100;
  }

  return {
    players: players.map((p) => ({
      player_id: p.playerId,
      name: p.playerName,
      team: p.team,
      opponent: p.opponent,
      position: p.position as OptimizeRequest['players'][number]['position'],
      salary: p.salary,
      projection: p.projection?.finalPoints ?? 0,
      ceiling: p.projection?.ceiling ?? p.projection?.finalPoints ?? 0,
      floor: p.projection?.floor ?? 0,
      ownership: p.projection?.projectedOwnership ?? 0,
      leverage: p.projection?.leverageScore ?? 0,
      game_id: p.gameId,
      locked: p.locked,
      excluded: p.excluded,
    })),
    roster_slots: rosterSlots,
    flex_positions: flexPositions,
    salary_cap: salaryCap,
    num_lineups: numLineups,
    min_salary: minSalary,
    max_salary: maxSalary,
    min_unique_players: minUnique,
    max_exposure: maxExposure,
    min_exposure: minExposure,
    global_max_ownership: globalMaxOwnership,
    min_total_projection: minTotalProjection,
    min_total_ceiling: minTotalCeiling,
    max_players_per_team: maxPerTeam,
    min_players_per_game: minPerGame,
    max_players_per_game: maxPerGame,
    locked_player_ids: players.filter((p) => p.locked).map((p) => p.playerId),
    excluded_player_ids: players.filter((p) => p.excluded).map((p) => p.playerId),
    groups: parseJsonArray<GroupRule>(formData, 'groupsJson', []),
    objective_weights: objectiveWeights,
    stack_rules: stackRules,
    random_seed: randomSeed,
    reproducible,
  };
}

export async function runOptimizerAction(_prev: LineupFormState, formData: FormData): Promise<LineupFormState> {
  const user = await requireUser();
  const slateId = String(formData.get('slateId') ?? '');
  const slate = await prisma.slate.findFirst({ where: { id: slateId, userId: user.id } });
  if (!slate) return { error: 'Slate not found.' };

  const players = await prisma.player.findMany({ where: { slateId }, include: { projection: true } });
  if (players.length === 0) {
    return { error: 'No players in this slate yet. Import a salary CSV first.' };
  }

  const presetName = String(formData.get('presetName') ?? 'Custom');
  const request = buildOptimizeRequest(formData, players);

  let response;
  try {
    response = await runOptimizer(request);
  } catch (err) {
    return { error: `Could not reach the optimizer service: ${(err as Error).message}` };
  }

  const run = await prisma.lineupRun.create({
    data: {
      userId: user.id,
      slateId,
      presetName,
      settingsJson: JSON.parse(JSON.stringify(request)),
      settingsVersion: response.settings_version,
      seedUsed: response.seed_used,
      warnings: response.warnings,
    },
  });

  // lineupPlayer.playerId must reference our internal Player.id, not the
  // external player_id used by the optimizer request — remap before persisting.
  const playerByExternalId = new Map(players.map((p) => [p.playerId, p]));
  for (const lineup of response.lineups) {
    const created = await prisma.lineup.create({
      data: {
        runId: run.id,
        externalLineupId: lineup.lineup_id,
        salaryUsed: lineup.salary_used,
        totalProjection: lineup.total_projection,
        totalCeiling: lineup.total_ceiling,
        totalOwnership: lineup.total_ownership,
        leverageScore: lineup.leverage_score,
        modelScore: lineup.model_score,
        stackSummary: lineup.stack_summary,
      },
    });
    await prisma.lineupPlayer.createMany({
      data: Object.entries(lineup.roster)
        .map(([slot, externalPlayerId]) => {
          const player = playerByExternalId.get(externalPlayerId);
          if (!player) return null;
          return { lineupId: created.id, playerId: player.id, slot };
        })
        .filter((r): r is { lineupId: string; playerId: string; slot: string } => r !== null),
    });
  }

  await logAudit(
    user.id,
    'optimizer.run',
    { presetName, requested: request.num_lineups, generated: response.lineups.length, warnings: response.warnings },
    { type: 'LineupRun', id: run.id }
  );

  revalidatePath('/lineups');
  revalidatePath('/portfolio');
  revalidatePath('/dashboard');

  return {
    success: `Generated ${response.lineups.length} of ${request.num_lineups} requested lineups. Labeled as model-ranked lineups — estimates, not guaranteed winners.`,
    lineupsGenerated: response.lineups.length,
    warnings: response.warnings,
  };
}

/**
 * Regenerates a single lineup in place, re-solving with the parent run's
 * original settings but the slate's *current* player pool (so a lock/exclude
 * or projection change made after the run is respected). Every other lineup
 * in the run is left untouched — this is "regenerate only affected lineups,"
 * applied one lineup at a time from Portfolio Review.
 */
export async function regenerateLineupAction(formData: FormData): Promise<LineupFormState> {
  const user = await requireUser();
  const lineupId = String(formData.get('lineupId') ?? '');

  const lineup = await prisma.lineup.findFirst({
    where: { id: lineupId, run: { userId: user.id } },
    include: { run: true },
  });
  if (!lineup) return { error: 'Lineup not found.' };

  const players = await prisma.player.findMany({ where: { slateId: lineup.run.slateId }, include: { projection: true } });
  const savedRequest = lineup.run.settingsJson as unknown as OptimizeRequest;

  const request: OptimizeRequest = {
    ...savedRequest,
    num_lineups: 1,
    players: players.map((p) => ({
      player_id: p.playerId,
      name: p.playerName,
      team: p.team,
      opponent: p.opponent,
      position: p.position as OptimizeRequest['players'][number]['position'],
      salary: p.salary,
      projection: p.projection?.finalPoints ?? 0,
      ceiling: p.projection?.ceiling ?? p.projection?.finalPoints ?? 0,
      floor: p.projection?.floor ?? 0,
      ownership: p.projection?.projectedOwnership ?? 0,
      leverage: p.projection?.leverageScore ?? 0,
      game_id: p.gameId,
      locked: p.locked,
      excluded: p.excluded,
    })),
    locked_player_ids: players.filter((p) => p.locked).map((p) => p.playerId),
    excluded_player_ids: players.filter((p) => p.excluded).map((p) => p.playerId),
  };

  let response;
  try {
    response = await runOptimizer(request);
  } catch (err) {
    return { error: `Could not reach the optimizer service: ${(err as Error).message}` };
  }
  if (response.lineups.length === 0) {
    return { error: `Could not find a replacement lineup with the current pool and settings. ${response.warnings.join(' ')}` };
  }

  const solved = response.lineups[0]!;
  const playerByExternalId = new Map(players.map((p) => [p.playerId, p]));

  await prisma.$transaction([
    prisma.lineupPlayer.deleteMany({ where: { lineupId: lineup.id } }),
    prisma.lineup.update({
      where: { id: lineup.id },
      data: {
        externalLineupId: solved.lineup_id,
        salaryUsed: solved.salary_used,
        totalProjection: solved.total_projection,
        totalCeiling: solved.total_ceiling,
        totalOwnership: solved.total_ownership,
        leverageScore: solved.leverage_score,
        modelScore: solved.model_score,
        stackSummary: solved.stack_summary,
      },
    }),
  ]);

  await prisma.lineupPlayer.createMany({
    data: Object.entries(solved.roster)
      .map(([slot, externalPlayerId]) => {
        const player = playerByExternalId.get(externalPlayerId);
        if (!player) return null;
        return { lineupId: lineup.id, playerId: player.id, slot };
      })
      .filter((r): r is { lineupId: string; playerId: string; slot: string } => r !== null),
  });

  await logAudit(user.id, 'optimizer.run', { scope: 'regenerate-single' }, { type: 'Lineup', id: lineup.id });
  revalidatePath('/portfolio');

  return { success: 'Lineup regenerated with the current player pool and the run\'s original settings.' };
}

export async function deleteLineupAction(formData: FormData) {
  const user = await requireUser();
  const lineupId = String(formData.get('lineupId') ?? '');
  const lineup = await prisma.lineup.findFirst({
    where: { id: lineupId, run: { userId: user.id } },
  });
  if (!lineup) return;
  await prisma.lineup.delete({ where: { id: lineupId } });
  await logAudit(user.id, 'lineup.delete', {}, { type: 'Lineup', id: lineupId });
  revalidatePath('/portfolio');
  revalidatePath('/lineups');
}

export async function deleteLineupRunAction(formData: FormData) {
  const user = await requireUser();
  const runId = String(formData.get('runId') ?? '');
  const run = await prisma.lineupRun.findFirst({ where: { id: runId, userId: user.id } });
  if (!run) return;
  await prisma.lineupRun.delete({ where: { id: runId } });
  await logAudit(user.id, 'lineup.delete', { scope: 'run' }, { type: 'LineupRun', id: runId });
  revalidatePath('/portfolio');
  revalidatePath('/lineups');
}
