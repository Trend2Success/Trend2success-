'use server';

import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';
import { runSimulation } from '@/lib/optimizer/client';
import { SimulateRequest } from '@/lib/optimizer/types';

export interface SimulationFormState {
  error?: string;
  success?: string;
  resultId?: string;
}

export async function runSimulationAction(_prev: SimulationFormState, formData: FormData): Promise<SimulationFormState> {
  const user = await requireUser();
  const slateId = String(formData.get('slateId') ?? '');
  const slate = await prisma.slate.findFirst({ where: { id: slateId, userId: user.id } });
  if (!slate) return { error: 'Slate not found.' };

  const players = await prisma.player.findMany({ where: { slateId }, include: { projection: true } });
  const withStats = players.filter((p) => p.projection && p.projection.standardDeviation !== null);
  if (withStats.length === 0) {
    return { error: 'No players have a standard deviation set yet. Import a projection CSV with standard_deviation filled in.' };
  }

  const distribution = (formData.get('distribution') as 'truncated_normal' | 'lognormal') || 'truncated_normal';
  const numSimulations = Math.max(1000, Math.min(20000, Number(formData.get('numSimulations') ?? 10000)));
  const threshold = formData.get('threshold') ? Number(formData.get('threshold')) : null;
  const reproducible = formData.get('reproducible') === 'true';
  const randomSeed = reproducible ? Number(formData.get('randomSeed') ?? 42) : null;

  const qbCorr = Number(formData.get('corrQbPassCatcher') ?? 0.6);
  const gameCorr = Number(formData.get('corrSameGame') ?? 0.15);
  const dstCorr = Number(formData.get('corrDstOpp') ?? -0.2);

  const lineupRunId = String(formData.get('lineupRunId') ?? '');
  let lineups: SimulateRequest['lineups'] = [];
  if (lineupRunId) {
    const dbLineups = await prisma.lineup.findMany({
      where: { runId: lineupRunId },
      include: { players: { include: { player: true } } },
    });
    lineups = dbLineups.map((l) => ({
      lineup_id: l.id,
      player_ids: l.players.map((lp) => lp.player.playerId),
      ownership_sum: l.totalOwnership,
    }));
  }

  const request: SimulateRequest = {
    players: withStats.map((p) => ({
      player_id: p.playerId,
      name: p.playerName,
      position: p.position,
      team: p.team,
      game_id: p.gameId,
      mean: p.projection!.finalPoints,
      stdev: p.projection!.standardDeviation ?? Math.max(1, p.projection!.finalPoints * 0.3),
    })),
    distribution,
    num_simulations: numSimulations,
    correlations: [],
    default_correlation_rules: {
      qb_own_pass_catcher: qbCorr,
      same_game_offense: gameCorr,
      dst_vs_opp_offense: dstCorr,
    },
    lineups,
    threshold,
    random_seed: randomSeed,
  };

  let response;
  try {
    response = await runSimulation(request);
  } catch (err) {
    return { error: `Could not reach the simulation service: ${(err as Error).message}` };
  }

  const record = await prisma.simulationRun.create({
    data: {
      userId: user.id,
      slateId,
      distribution,
      numSimulations,
      settingsJson: JSON.parse(JSON.stringify(request)),
      resultsJson: JSON.parse(JSON.stringify(response)),
      seedUsed: response.seed_used,
    },
  });

  await logAudit(user.id, 'simulation.run', { numSimulations, distribution }, { type: 'SimulationRun', id: record.id });
  revalidatePath('/simulation');

  return { success: `Ran ${numSimulations.toLocaleString()} simulations. All figures are estimates from your input distributions, not predictions.`, resultId: record.id };
}
