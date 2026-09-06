// Seeds SlateEdge with a single demo account and a fully fictional NFL
// slate so every screen has something to show before any real CSV is
// uploaded. All names, teams, and numbers below are invented for
// demonstration only and are clearly labeled "Demo Data".
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';
import {
  value as calcValue,
  ceilingValue as calcCeilingValue,
  leverageScores,
  percentileRank,
  isChalk,
  isContrarian,
} from '../src/lib/calculations';

const prisma = new PrismaClient();

interface DemoPlayer {
  playerId: string;
  playerName: string;
  team: string;
  opponent: string;
  position: 'QB' | 'RB' | 'WR' | 'TE' | 'DST';
  salary: number;
  gameInfo: string;
  projectedPoints: number;
  floor: number;
  ceiling: number;
  standardDeviation: number;
  projectedOwnership: number;
}

// Two fictional games, fictional team codes (not real NFL abbreviations).
const DEMO_PLAYERS: DemoPlayer[] = [
  { playerId: 'DEMO_QB_1', playerName: 'Demo Player QB1', team: 'FOX', opponent: 'WLF', position: 'QB', salary: 7500, gameInfo: 'FOX@WLF', projectedPoints: 19.8, floor: 12, ceiling: 30, standardDeviation: 6.2, projectedOwnership: 18 },
  { playerId: 'DEMO_QB_2', playerName: 'Demo Player QB2', team: 'WLF', opponent: 'FOX', position: 'QB', salary: 6800, gameInfo: 'FOX@WLF', projectedPoints: 17.9, floor: 10, ceiling: 27, standardDeviation: 5.8, projectedOwnership: 12 },
  { playerId: 'DEMO_QB_3', playerName: 'Demo Player QB3', team: 'HWK', opponent: 'BER', position: 'QB', salary: 6200, gameInfo: 'HWK@BER', projectedPoints: 16.5, floor: 9, ceiling: 26, standardDeviation: 6.0, projectedOwnership: 9 },
  { playerId: 'DEMO_RB_1', playerName: 'Demo Player RB1', team: 'FOX', opponent: 'WLF', position: 'RB', salary: 8200, gameInfo: 'FOX@WLF', projectedPoints: 18.2, floor: 8, ceiling: 32, standardDeviation: 7.5, projectedOwnership: 32 },
  { playerId: 'DEMO_RB_2', playerName: 'Demo Player RB2', team: 'WLF', opponent: 'FOX', position: 'RB', salary: 6900, gameInfo: 'FOX@WLF', projectedPoints: 14.1, floor: 6, ceiling: 24, standardDeviation: 6.1, projectedOwnership: 21 },
  { playerId: 'DEMO_RB_3', playerName: 'Demo Player RB3', team: 'HWK', opponent: 'BER', position: 'RB', salary: 5400, gameInfo: 'HWK@BER', projectedPoints: 11.6, floor: 4, ceiling: 21, standardDeviation: 5.7, projectedOwnership: 14 },
  { playerId: 'DEMO_RB_4', playerName: 'Demo Player RB4', team: 'BER', opponent: 'HWK', position: 'RB', salary: 4800, gameInfo: 'HWK@BER', projectedPoints: 9.8, floor: 3, ceiling: 19, standardDeviation: 5.4, projectedOwnership: 8 },
  { playerId: 'DEMO_RB_5', playerName: 'Demo Player RB5', team: 'ORC', opponent: 'LNX', position: 'RB', salary: 4200, gameInfo: 'ORC@LNX', projectedPoints: 8.4, floor: 2, ceiling: 17, standardDeviation: 5.0, projectedOwnership: 5 },
  { playerId: 'DEMO_WR_1', playerName: 'Demo Player WR1', team: 'FOX', opponent: 'WLF', position: 'WR', salary: 7900, gameInfo: 'FOX@WLF', projectedPoints: 16.4, floor: 6, ceiling: 29, standardDeviation: 7.8, projectedOwnership: 27 },
  { playerId: 'DEMO_WR_2', playerName: 'Demo Player WR2', team: 'FOX', opponent: 'WLF', position: 'WR', salary: 6100, gameInfo: 'FOX@WLF', projectedPoints: 12.9, floor: 4, ceiling: 24, standardDeviation: 6.9, projectedOwnership: 16 },
  { playerId: 'DEMO_WR_3', playerName: 'Demo Player WR3', team: 'WLF', opponent: 'FOX', position: 'WR', salary: 7200, gameInfo: 'FOX@WLF', projectedPoints: 14.8, floor: 5, ceiling: 26, standardDeviation: 7.1, projectedOwnership: 22 },
  { playerId: 'DEMO_WR_4', playerName: 'Demo Player WR4', team: 'WLF', opponent: 'FOX', position: 'WR', salary: 5300, gameInfo: 'FOX@WLF', projectedPoints: 10.6, floor: 3, ceiling: 20, standardDeviation: 6.0, projectedOwnership: 11 },
  { playerId: 'DEMO_WR_5', playerName: 'Demo Player WR5', team: 'HWK', opponent: 'BER', position: 'WR', salary: 6600, gameInfo: 'HWK@BER', projectedPoints: 13.2, floor: 4, ceiling: 25, standardDeviation: 7.0, projectedOwnership: 17 },
  { playerId: 'DEMO_WR_6', playerName: 'Demo Player WR6', team: 'BER', opponent: 'HWK', position: 'WR', salary: 5700, gameInfo: 'HWK@BER', projectedPoints: 11.1, floor: 3, ceiling: 21, standardDeviation: 6.3, projectedOwnership: 13 },
  { playerId: 'DEMO_WR_7', playerName: 'Demo Player WR7', team: 'ORC', opponent: 'LNX', position: 'WR', salary: 4900, gameInfo: 'ORC@LNX', projectedPoints: 9.4, floor: 2, ceiling: 18, standardDeviation: 5.8, projectedOwnership: 7 },
  { playerId: 'DEMO_WR_8', playerName: 'Demo Player WR8', team: 'LNX', opponent: 'ORC', position: 'WR', salary: 4400, gameInfo: 'ORC@LNX', projectedPoints: 8.1, floor: 2, ceiling: 16, standardDeviation: 5.3, projectedOwnership: 5 },
  { playerId: 'DEMO_TE_1', playerName: 'Demo Player TE1', team: 'FOX', opponent: 'WLF', position: 'TE', salary: 5600, gameInfo: 'FOX@WLF', projectedPoints: 11.3, floor: 4, ceiling: 20, standardDeviation: 5.4, projectedOwnership: 19 },
  { playerId: 'DEMO_TE_2', playerName: 'Demo Player TE2', team: 'HWK', opponent: 'BER', position: 'TE', salary: 4300, gameInfo: 'HWK@BER', projectedPoints: 8.2, floor: 2, ceiling: 16, standardDeviation: 4.8, projectedOwnership: 10 },
  { playerId: 'DEMO_TE_3', playerName: 'Demo Player TE3', team: 'ORC', opponent: 'LNX', position: 'TE', salary: 3600, gameInfo: 'ORC@LNX', projectedPoints: 6.1, floor: 1, ceiling: 13, standardDeviation: 4.2, projectedOwnership: 4 },
  { playerId: 'DEMO_DST_1', playerName: 'Demo Defense FOX', team: 'FOX', opponent: 'WLF', position: 'DST', salary: 3200, gameInfo: 'FOX@WLF', projectedPoints: 7.8, floor: 1, ceiling: 16, standardDeviation: 5.1, projectedOwnership: 15 },
  { playerId: 'DEMO_DST_2', playerName: 'Demo Defense HWK', team: 'HWK', opponent: 'BER', position: 'DST', salary: 2800, gameInfo: 'HWK@BER', projectedPoints: 6.4, floor: 0, ceiling: 14, standardDeviation: 4.7, projectedOwnership: 9 },
  { playerId: 'DEMO_DST_3', playerName: 'Demo Defense ORC', team: 'ORC', opponent: 'LNX', position: 'DST', salary: 2400, gameInfo: 'ORC@LNX', projectedPoints: 5.6, floor: 0, ceiling: 12, standardDeviation: 4.3, projectedOwnership: 6 },
];

function gameId(team: string, opponent: string): string {
  return [team, opponent].sort().join('_');
}

async function main() {
  const email = 'demo@slateedge.local';
  const passwordHash = await bcrypt.hash('DemoPassword123!', 12);

  const user = await prisma.user.upsert({
    where: { email },
    update: {},
    create: {
      email,
      passwordHash,
      displayName: 'Demo User',
      settings: { create: {} },
    },
  });

  const contestDate = new Date();
  contestDate.setUTCDate(contestDate.getUTCDate() + ((7 - contestDate.getUTCDay()) % 7 || 7));
  contestDate.setUTCHours(17, 0, 0, 0);

  const slate = await prisma.slate.upsert({
    where: { userId_slateId: { userId: user.id, slateId: 'DEMO_SLATE_1' } },
    update: {},
    create: {
      userId: user.id,
      slateId: 'DEMO_SLATE_1',
      slateName: 'Demo Sunday Main Slate',
      sport: 'NFL',
      contestDate,
      isDemo: true,
    },
  });

  const players = [];
  for (const dp of DEMO_PLAYERS) {
    const player = await prisma.player.upsert({
      where: { slateId_playerId: { slateId: slate.id, playerId: dp.playerId } },
      update: {},
      create: {
        slateId: slate.id,
        playerId: dp.playerId,
        playerName: dp.playerName,
        team: dp.team,
        opponent: dp.opponent,
        position: dp.position,
        rosterPositions: dp.position,
        salary: dp.salary,
        gameInfo: dp.gameInfo,
        gameId: gameId(dp.team, dp.opponent),
        status: 'ACTIVE',
      },
    });
    players.push({ player, demo: dp });
  }

  const source = await prisma.projectionSource.upsert({
    where: { slateId_sourceLabel: { slateId: slate.id, sourceLabel: 'Demo Data' } },
    update: {},
    create: { slateId: slate.id, sourceLabel: 'Demo Data' },
  });

  for (const { player, demo } of players) {
    await prisma.projectionRow.upsert({
      where: { sourceId_playerId: { sourceId: source.id, playerId: demo.playerId } },
      update: {},
      create: {
        sourceId: source.id,
        playerId: demo.playerId,
        playerName: demo.playerName,
        projectedPoints: demo.projectedPoints,
        floor: demo.floor,
        ceiling: demo.ceiling,
        standardDeviation: demo.standardDeviation,
        projectedOwnership: demo.projectedOwnership,
        notes: 'Demo Data — Not Real Players or Projections',
      },
    });

    await prisma.projectionSnapshot.upsert({
      where: { playerId: player.id },
      update: {},
      create: {
        playerId: player.id,
        basePoints: demo.projectedPoints,
        finalPoints: demo.projectedPoints,
        floor: demo.floor,
        ceiling: demo.ceiling,
        standardDeviation: demo.standardDeviation,
        projectedOwnership: demo.projectedOwnership,
      },
    });
  }

  await prisma.importBatch.create({
    data: {
      slateId: slate.id,
      kind: 'salary',
      sourceLabel: 'Demo Data',
      fileName: 'demo-seed',
      rowCount: DEMO_PLAYERS.length,
      errorCount: 0,
    },
  });
  await prisma.importBatch.create({
    data: {
      slateId: slate.id,
      kind: 'projection',
      sourceLabel: 'Demo Data',
      fileName: 'demo-seed',
      rowCount: DEMO_PLAYERS.length,
      errorCount: 0,
    },
  });

  // Recompute value/ceiling-value/leverage/chalk/contrarian for the whole slate.
  const ceilings = DEMO_PLAYERS.map((p) => p.ceiling);
  const ownerships = DEMO_PLAYERS.map((p) => p.projectedOwnership);
  const leverages = leverageScores(DEMO_PLAYERS.map((p) => ({ ceiling: p.ceiling, ownership: p.projectedOwnership })));

  for (const [i, { player, demo }] of players.entries()) {
    const ceilingPctile = percentileRank(demo.ceiling, ceilings);
    await prisma.projectionSnapshot.update({
      where: { playerId: player.id },
      data: {
        value: calcValue(demo.projectedPoints, demo.salary),
        ceilingValue: calcCeilingValue(demo.ceiling, demo.salary),
        leverageScore: leverages[i],
        chalkFlag: isChalk(demo.projectedOwnership, 25),
        contrarianFlag: isContrarian(demo.projectedOwnership, ceilingPctile, 8, 70),
      },
    });
  }

  // A small demo lineup run so Portfolio Review / Simulation Lab aren't empty.
  const existingRun = await prisma.lineupRun.findFirst({ where: { slateId: slate.id, presetName: 'Demo' } });
  if (!existingRun) {
    const run = await prisma.lineupRun.create({
      data: {
        userId: user.id,
        slateId: slate.id,
        presetName: 'Demo',
        settingsJson: { note: 'Seed demo lineup, not optimizer output' },
        settingsVersion: '1.0',
        warnings: [],
      },
    });

    const byId = Object.fromEntries(players.map((p) => [p.demo.playerId, p.player]));
    const rosterMap: Record<string, string> = {
      QB: 'DEMO_QB_1',
      RB1: 'DEMO_RB_1',
      RB2: 'DEMO_RB_2',
      WR1: 'DEMO_WR_1',
      WR2: 'DEMO_WR_3',
      WR3: 'DEMO_WR_5',
      TE: 'DEMO_TE_1',
      FLEX: 'DEMO_RB_3',
      DST: 'DEMO_DST_1',
    };
    const rosterPlayers = Object.values(rosterMap).map((pid) => byId[pid]);
    const salaryUsed = rosterPlayers.reduce((s, p) => s + p!.salary, 0);
    const demoById = Object.fromEntries(DEMO_PLAYERS.map((d) => [d.playerId, d]));
    const totalProjection = Object.values(rosterMap).reduce((s, pid) => s + demoById[pid]!.projectedPoints, 0);
    const totalCeiling = Object.values(rosterMap).reduce((s, pid) => s + demoById[pid]!.ceiling, 0);
    const totalOwnership = Object.values(rosterMap).reduce((s, pid) => s + demoById[pid]!.projectedOwnership, 0);

    const lineup = await prisma.lineup.create({
      data: {
        runId: run.id,
        externalLineupId: 'demo-lineup-1',
        salaryUsed,
        totalProjection,
        totalCeiling,
        totalOwnership,
        leverageScore: 0.1,
        modelScore: totalProjection,
        stackSummary: 'QB Demo Player QB1 (FOX) stacked with 1 pass-catcher (Demo Player WR1, FOX). No bring-back.',
      },
    });

    await prisma.lineupPlayer.createMany({
      data: Object.entries(rosterMap).map(([slot, pid]) => ({ lineupId: lineup.id, playerId: byId[pid]!.id, slot })),
    });
  }

  console.log(`Seeded demo user ${email} (password: DemoPassword123!) with slate "${slate.slateName}".`);
}

main()
  .catch((err) => {
    console.error(err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
