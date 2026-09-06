import { describe, expect, it } from 'vitest';
import { parseAndValidate } from '@/lib/csv/engine';
import { SALARY_COLUMNS, salaryRowSchema } from '@/lib/csv/salary';

const HEADER =
  'slate_id,slate_name,sport,contest_date,player_id,player_name,team,opponent,position,roster_positions,salary,game_info,start_time,status';

function row(overrides: Partial<Record<string, string>> = {}): string {
  const base: Record<string, string> = {
    slate_id: 'S1',
    slate_name: 'Demo Slate',
    sport: 'NFL',
    contest_date: '2026-09-13',
    player_id: 'P1',
    player_name: 'Demo Player',
    team: 'AAA',
    opponent: 'BBB',
    position: 'QB',
    roster_positions: 'QB',
    salary: '7000',
    game_info: 'AAA@BBB',
    start_time: '2026-09-13T13:00:00Z',
    status: 'ACTIVE',
  };
  const merged = { ...base, ...overrides };
  return [
    merged.slate_id,
    merged.slate_name,
    merged.sport,
    merged.contest_date,
    merged.player_id,
    merged.player_name,
    merged.team,
    merged.opponent,
    merged.position,
    merged.roster_positions,
    merged.salary,
    merged.game_info,
    merged.start_time,
    merged.status,
  ].join(',');
}

describe('salary CSV validation', () => {
  it('accepts a well-formed row', () => {
    const csv = `${HEADER}\n${row()}`;
    const result = parseAndValidate(csv, SALARY_COLUMNS, salaryRowSchema);
    expect(result.errors).toHaveLength(0);
    expect(result.validRows).toHaveLength(1);
    expect(result.validRows[0]?.salary).toBe(7000);
  });

  it('maps a common header alias (Salary -> salary) case-insensitively', () => {
    const csv = HEADER.replace('salary', 'Sal') + `\n${row()}`;
    const result = parseAndValidate(csv, SALARY_COLUMNS, salaryRowSchema);
    expect(result.unmatchedRequired).toHaveLength(0);
    expect(result.validRows).toHaveLength(1);
  });

  it('flags an invalid position value', () => {
    const csv = `${HEADER}\n${row({ position: 'K' })}`;
    const result = parseAndValidate(csv, SALARY_COLUMNS, salaryRowSchema);
    expect(result.validRows).toHaveLength(0);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]?.messages.join(' ')).toMatch(/position/i);
  });

  it('flags a missing/non-numeric salary', () => {
    const csv = `${HEADER}\n${row({ salary: 'not-a-number' })}`;
    const result = parseAndValidate(csv, SALARY_COLUMNS, salaryRowSchema);
    expect(result.validRows).toHaveLength(0);
    expect(result.errors[0]?.messages.join(' ')).toMatch(/salary/i);
  });

  it('flags a zero or negative salary as impossible', () => {
    const csv = `${HEADER}\n${row({ salary: '0' })}`;
    const result = parseAndValidate(csv, SALARY_COLUMNS, salaryRowSchema);
    expect(result.validRows).toHaveLength(0);
  });

  it('deduplicates rows with a duplicate player_id', () => {
    const csv = `${HEADER}\n${row()}\n${row({ player_name: 'Duplicate Entry' })}`;
    const result = parseAndValidate(csv, SALARY_COLUMNS, salaryRowSchema, { dedupeKey: (r) => r.player_id });
    expect(result.validRows).toHaveLength(1);
    expect(result.duplicatesRemoved).toBe(1);
  });

  it('reports missing required columns instead of throwing', () => {
    const csv = 'player_id,player_name\nP1,Demo Player';
    const result = parseAndValidate(csv, SALARY_COLUMNS, salaryRowSchema);
    expect(result.unmatchedRequired.length).toBeGreaterThan(0);
    expect(result.validRows).toHaveLength(0);
  });
});
