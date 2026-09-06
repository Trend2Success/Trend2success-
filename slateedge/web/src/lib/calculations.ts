// Transparent, plain-formula calculations shared by the Projection Lab and
// the Ownership & Leverage screens. Every function here is a simple,
// documented arithmetic rule — nothing here is a black box, and none of it
// is a prediction or guarantee of real-world outcomes.

export function value(projectedPoints: number, salary: number): number {
  if (salary <= 0) return 0;
  return projectedPoints / (salary / 1000);
}

export function ceilingValue(ceiling: number, salary: number): number {
  if (salary <= 0) return 0;
  return ceiling / (salary / 1000);
}

/** 0-100 percentile rank of `value` within `population` (inclusive, average-rank tie handling). */
export function percentileRank(value: number, population: number[]): number {
  if (population.length === 0) return 50;
  const sorted = [...population].sort((a, b) => a - b);
  let countBelow = 0;
  let countEqual = 0;
  for (const v of sorted) {
    if (v < value) countBelow += 1;
    else if (v === value) countEqual += 1;
  }
  const rank = countBelow + countEqual / 2;
  return (rank / sorted.length) * 100;
}

export interface LeverageInput {
  ceiling: number;
  ownership: number;
}

/**
 * leverage score = normalized ceiling percentile - normalized ownership percentile,
 * scaled to roughly [-1, 1]. Positive means "ceiling rank exceeds ownership rank"
 * (a plain description, not a claim the player is a good or bad play on its own).
 */
export function leverageScores(players: LeverageInput[]): number[] {
  const ceilings = players.map((p) => p.ceiling);
  const ownerships = players.map((p) => p.ownership);
  return players.map((p) => {
    const ceilPct = percentileRank(p.ceiling, ceilings);
    const ownPct = percentileRank(p.ownership, ownerships);
    return Number(((ceilPct - ownPct) / 100).toFixed(4));
  });
}

export function ceilingToOwnershipRatio(ceiling: number, ownership: number): number | null {
  if (ownership <= 0) return null;
  return Number((ceiling / ownership).toFixed(3));
}

export function isChalk(ownership: number, thresholdPct: number): boolean {
  return ownership >= thresholdPct;
}

export function isContrarian(
  ownership: number,
  ceilingPercentile: number,
  ownershipThresholdPct: number,
  ceilingPercentileThreshold: number
): boolean {
  return ownership <= ownershipThresholdPct && ceilingPercentile >= ceilingPercentileThreshold;
}

export function applyManualAdjustment(
  basePoints: number,
  kind: 'points' | 'percent',
  delta: number
): number {
  if (kind === 'points') return Number((basePoints + delta).toFixed(2));
  return Number((basePoints * (1 + delta / 100)).toFixed(2));
}

export interface BlendSource {
  points: number;
  weight: number;
}

export function blendProjections(sources: BlendSource[]): number {
  const totalWeight = sources.reduce((sum, s) => sum + s.weight, 0);
  if (totalWeight <= 0) return 0;
  const weighted = sources.reduce((sum, s) => sum + s.points * s.weight, 0);
  return Number((weighted / totalWeight).toFixed(2));
}
