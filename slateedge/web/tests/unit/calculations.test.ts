import { describe, expect, it } from 'vitest';
import {
  value,
  ceilingValue,
  percentileRank,
  leverageScores,
  ceilingToOwnershipRatio,
  isChalk,
  isContrarian,
  applyManualAdjustment,
  blendProjections,
} from '@/lib/calculations';

describe('value / ceilingValue', () => {
  it('computes points per $1000 of salary', () => {
    expect(value(20, 5000)).toBeCloseTo(4, 5);
    expect(ceilingValue(30, 5000)).toBeCloseTo(6, 5);
  });

  it('returns 0 for non-positive salary instead of dividing by zero', () => {
    expect(value(20, 0)).toBe(0);
    expect(ceilingValue(20, -100)).toBe(0);
  });
});

describe('percentileRank', () => {
  it('ranks the minimum near 0 and the maximum near 100', () => {
    const pop = [10, 20, 30, 40, 50];
    expect(percentileRank(10, pop)).toBeCloseTo(10, 5);
    expect(percentileRank(50, pop)).toBeCloseTo(90, 5);
  });

  it('handles ties by averaging rank', () => {
    const pop = [10, 10, 20, 20];
    expect(percentileRank(10, pop)).toBeCloseTo(25, 5);
  });

  it('defaults to 50 for an empty population', () => {
    expect(percentileRank(10, [])).toBe(50);
  });
});

describe('leverageScores', () => {
  it('gives positive leverage to high ceiling / low ownership players', () => {
    const players = [
      { ceiling: 30, ownership: 5 }, // high ceiling, low ownership -> positive leverage
      { ceiling: 10, ownership: 40 }, // low ceiling, high ownership -> negative leverage
    ];
    const [a, b] = leverageScores(players);
    expect(a).toBeGreaterThan(0);
    expect(b).toBeLessThan(0);
  });

  it('stays within roughly [-1, 1]', () => {
    const players = Array.from({ length: 10 }, (_, i) => ({ ceiling: i, ownership: 10 - i }));
    for (const score of leverageScores(players)) {
      expect(score).toBeGreaterThanOrEqual(-1);
      expect(score).toBeLessThanOrEqual(1);
    }
  });
});

describe('ceilingToOwnershipRatio', () => {
  it('divides ceiling by ownership', () => {
    expect(ceilingToOwnershipRatio(30, 10)).toBeCloseTo(3, 5);
  });
  it('returns null when ownership is zero or negative', () => {
    expect(ceilingToOwnershipRatio(30, 0)).toBeNull();
    expect(ceilingToOwnershipRatio(30, -1)).toBeNull();
  });
});

describe('chalk / contrarian flags', () => {
  it('flags chalk at or above the threshold', () => {
    expect(isChalk(25, 25)).toBe(true);
    expect(isChalk(24.9, 25)).toBe(false);
  });

  it('flags contrarian only when low-owned AND high-ceiling-percentile', () => {
    expect(isContrarian(5, 80, 8, 70)).toBe(true);
    expect(isContrarian(20, 80, 8, 70)).toBe(false); // too highly owned
    expect(isContrarian(5, 50, 8, 70)).toBe(false); // ceiling percentile too low
  });
});

describe('applyManualAdjustment', () => {
  it('adds flat points', () => {
    expect(applyManualAdjustment(20, 'points', 3)).toBe(23);
  });
  it('applies a percent delta', () => {
    expect(applyManualAdjustment(20, 'percent', 10)).toBe(22);
    expect(applyManualAdjustment(20, 'percent', -10)).toBe(18);
  });
});

describe('blendProjections', () => {
  it('weights sources proportionally', () => {
    const blended = blendProjections([
      { points: 10, weight: 1 },
      { points: 20, weight: 3 },
    ]);
    expect(blended).toBeCloseTo(17.5, 5);
  });

  it('returns 0 when total weight is zero', () => {
    expect(blendProjections([{ points: 10, weight: 0 }])).toBe(0);
  });
});
