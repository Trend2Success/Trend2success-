import { describe, expect, it } from 'vitest';
import { parseAndValidate } from '@/lib/csv/engine';
import { PROJECTION_COLUMNS, projectionRowSchema } from '@/lib/csv/projection';

const HEADER =
  'player_id,player_name,projected_points,floor,ceiling,standard_deviation,projected_ownership,expected_minutes_or_snaps,target_share_or_usage,notes,projection_source,last_updated';

function row(overrides: Partial<Record<string, string>> = {}): string {
  const base: Record<string, string> = {
    player_id: 'P1',
    player_name: 'Demo Player',
    projected_points: '18.5',
    floor: '10',
    ceiling: '28',
    standard_deviation: '6',
    projected_ownership: '15',
    expected_minutes_or_snaps: '60',
    target_share_or_usage: '',
    notes: '',
    projection_source: 'User Upload',
    last_updated: '2026-09-06T12:00:00Z',
  };
  const merged = { ...base, ...overrides };
  return Object.values(merged).join(',');
}

describe('projection CSV validation', () => {
  it('accepts a well-formed row', () => {
    const csv = `${HEADER}\n${row()}`;
    const result = parseAndValidate(csv, PROJECTION_COLUMNS, projectionRowSchema, { dedupeKey: (r) => r.player_id });
    expect(result.errors).toHaveLength(0);
    expect(result.validRows).toHaveLength(1);
  });

  it('rejects a floor greater than the projection (impossible value)', () => {
    const csv = `${HEADER}\n${row({ floor: '25', projected_points: '18.5' })}`;
    const result = parseAndValidate(csv, PROJECTION_COLUMNS, projectionRowSchema);
    expect(result.validRows).toHaveLength(0);
    expect(result.errors[0]?.messages.join(' ')).toMatch(/floor/i);
  });

  it('rejects a ceiling below the projection (impossible value)', () => {
    const csv = `${HEADER}\n${row({ ceiling: '5', projected_points: '18.5' })}`;
    const result = parseAndValidate(csv, PROJECTION_COLUMNS, projectionRowSchema);
    expect(result.validRows).toHaveLength(0);
    expect(result.errors[0]?.messages.join(' ')).toMatch(/ceiling/i);
  });

  it('rejects ownership outside 0-100', () => {
    const csv = `${HEADER}\n${row({ projected_ownership: '150' })}`;
    const result = parseAndValidate(csv, PROJECTION_COLUMNS, projectionRowSchema);
    expect(result.validRows).toHaveLength(0);
  });

  it('allows optional numeric fields to be blank', () => {
    const csv = `${HEADER}\n${row({ floor: '', ceiling: '', standard_deviation: '', projected_ownership: '' })}`;
    const result = parseAndValidate(csv, PROJECTION_COLUMNS, projectionRowSchema);
    expect(result.errors).toHaveLength(0);
    expect(result.validRows[0]?.floor).toBeNull();
  });
});
