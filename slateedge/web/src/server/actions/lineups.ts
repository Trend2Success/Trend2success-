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
} from '@/lib/optimizer/types';

export interface LineupFormState {
  error?: string;
  success?: string;
  lineupsGenerated?: number;
  warnings?: string[];
}

function parseGroupsFromForm(formData: FormData): GroupRule[] {
  const raw = formData.get('groupsJson');
  if (!raw) return [];
  try {
    const parsed = JSON.parse(String(raw));
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function runOptimizerAction(_prev: LineupFormState, formData: FormData): Promise<LineupFormState> {
  const user = await requireUser();
  const slateId = String(formData.get('slateId') ?? '');
  const slate = await prisma.slate.findFirst({ where: { id: slateId, userId: user.id } });
  if (!slate) return { error: 'Slate not found.' };

  const players = await prisma.player.findMany({
    where: { slateId },
    include: { projection: true },
  });
  if (players.length === 0) {
    return { error: 'No players in this slate yet. Import a salary CSV first.' };
  }

  const presetName = String(formData.get('presetName') ?? 'Custom');
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
  const maxExposure: Record<string, number> = {};
  const minExposure: Record<string, number> = {};
  if (globalMaxExposurePct !== null) {
    for (const p of players) maxExposure[p.playerId] = globalMaxExposurePct / 100;
  }

  const request: OptimizeRequest = {
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
    roster_slots: DEFAULT_ROSTER_SLOTS,
    flex_positions: DEFAULT_FLEX_POSITIONS,
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
    groups: parseGroupsFromForm(formData),
    objective_weights: objectiveWeights,
    stack_rules: stackRules,
    random_seed: randomSeed,
    reproducible,
  };

  let response;
  try {
    response = await runOptimizer(request);
  } catch (err) {
    return { error: `Could not reach the optimizer service: ${(err as Error).message}` };
  }

  const playerByExternalId = new Map(players.map((p) => [p.playerId, p]));

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
    { presetName, requested: numLineups, generated: response.lineups.length, warnings: response.warnings },
    { type: 'LineupRun', id: run.id }
  );

  revalidatePath('/lineups');
  revalidatePath('/portfolio');
  revalidatePath('/dashboard');

  return {
    success: `Generated ${response.lineups.length} of ${numLineups} requested lineups. Labeled as model-ranked lineups — estimates, not guaranteed winners.`,
    lineupsGenerated: response.lineups.length,
    warnings: response.warnings,
  };
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
