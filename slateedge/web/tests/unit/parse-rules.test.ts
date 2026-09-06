import { describe, expect, it } from 'vitest';
import { parsePlainEnglishRules } from '@/lib/ai-assistant/parseRules';

describe('parsePlainEnglishRules', () => {
  it('parses the documented example instruction end-to-end', () => {
    const result = parsePlainEnglishRules(
      'Build 20 tournament lineups with QB stacks, no more than 40% exposure to any player, at least $49,000 salary used, and reduce exposure to highly owned RBs.'
    );
    expect(result.patch.num_lineups).toBe(20);
    expect(result.patch.global_max_exposure_pct).toBe(40);
    expect(result.patch.min_salary).toBe(49000);
    expect(result.patch.stack_rules?.qb_stack_min).toBe(1);
    expect(result.patch.objective_weights?.ownership_penalty).toBeGreaterThan(0);
    expect(result.assumptions.length).toBeGreaterThan(0);
  });

  it('never proposes a guarantee and flags unrecognized input for clarification', () => {
    const result = parsePlainEnglishRules('just win please');
    expect(result.clarificationsNeeded.length).toBeGreaterThan(0);
    expect(Object.keys(result.patch)).toHaveLength(0);
  });

  it('recognizes bring-back and RB/QB exclusion phrasing', () => {
    const result = parsePlainEnglishRules('Use a QB stack with bring-back, and no RB with QB.');
    expect(result.patch.stack_rules?.bring_back_min).toBe(1);
    expect(result.patch.stack_rules?.allow_rb_with_qb).toBe(false);
  });
});
