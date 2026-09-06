import { prisma } from '@/lib/db';
import {
  value as calcValue,
  ceilingValue as calcCeilingValue,
  leverageScores,
  percentileRank,
  isChalk,
  isContrarian,
} from '@/lib/calculations';

/**
 * Recomputes value, ceiling value, leverage score, and chalk/contrarian flags
 * for every player on a slate, using that slate's current ProjectionSnapshot
 * rows and the user's configured thresholds. Called after salary imports,
 * projection imports, blend changes, and manual adjustments so the whole
 * slate stays internally consistent.
 */
export async function recomputeSlateAnalytics(slateId: string, userId: string) {
  const [players, settings] = await Promise.all([
    prisma.player.findMany({
      where: { slateId },
      include: { projection: true },
    }),
    prisma.settings.findUnique({ where: { userId } }),
  ]);

  const chalkThreshold = settings?.chalkThresholdPct ?? 25;
  const contrarianOwnership = settings?.contrarianOwnershipPct ?? 8;
  const contrarianCeilingPctile = settings?.contrarianCeilingPctile ?? 70;

  const withSnapshots = players.filter((p) => p.projection);
  const ceilings = withSnapshots.map((p) => p.projection!.ceiling ?? p.projection!.finalPoints);
  const ownerships = withSnapshots.map((p) => p.projection!.projectedOwnership ?? 0);
  const leverages = leverageScores(
    withSnapshots.map((p, i) => ({ ceiling: ceilings[i]!, ownership: ownerships[i]! }))
  );

  await prisma.$transaction(
    withSnapshots.map((p, i) => {
      const snap = p.projection!;
      const ceiling = snap.ceiling ?? snap.finalPoints;
      const ownership = snap.projectedOwnership ?? 0;
      const ceilingPctile = percentileRank(ceiling, ceilings);

      return prisma.projectionSnapshot.update({
        where: { playerId: p.id },
        data: {
          value: calcValue(snap.finalPoints, p.salary),
          ceilingValue: calcCeilingValue(ceiling, p.salary),
          leverageScore: leverages[i],
          chalkFlag: isChalk(ownership, chalkThreshold),
          contrarianFlag: isContrarian(ownership, ceilingPctile, contrarianOwnership, contrarianCeilingPctile),
        },
      });
    })
  );
}

export function deriveGameId(team: string, opponent: string): string {
  return [team, opponent].sort().join('_');
}
