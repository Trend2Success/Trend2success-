import { z } from 'zod';
import { ColumnSpec } from './columnMap';

export const VALID_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST'] as const;

export const SALARY_COLUMNS: ColumnSpec[] = [
  { key: 'slate_id', required: true, aliases: ['slateid', 'slate'] },
  { key: 'slate_name', required: true, aliases: ['slate_name', 'slate name', 'slatename'] },
  { key: 'sport', required: false, aliases: [] },
  { key: 'contest_date', required: true, aliases: ['date', 'contest date'] },
  { key: 'player_id', required: true, aliases: ['id', 'dk_id', 'dkid', 'player id'] },
  { key: 'player_name', required: true, aliases: ['name', 'player'] },
  { key: 'team', required: true, aliases: ['tm', 'teamabbrev'] },
  { key: 'opponent', required: true, aliases: ['opp'] },
  { key: 'position', required: true, aliases: ['pos'] },
  { key: 'roster_positions', required: false, aliases: ['roster position', 'eligible positions'] },
  { key: 'salary', required: true, aliases: ['sal'] },
  { key: 'game_info', required: false, aliases: ['game', 'game info'] },
  { key: 'start_time', required: false, aliases: ['time', 'kickoff'] },
  { key: 'status', required: false, aliases: ['injury status'] },
];

export const salaryRowSchema = z.object({
  slate_id: z.string().min(1, 'slate_id is required'),
  slate_name: z.string().min(1, 'slate_name is required'),
  sport: z
    .string()
    .transform((v) => (v ? v.toUpperCase() : 'NFL'))
    .default('NFL'),
  contest_date: z.string().refine((v) => v !== '' && !Number.isNaN(Date.parse(v)), 'invalid contest_date'),
  player_id: z.string().min(1, 'player_id is required'),
  player_name: z.string().min(1, 'player_name is required'),
  team: z
    .string()
    .min(1, 'team is required')
    .transform((v) => v.toUpperCase()),
  opponent: z
    .string()
    .min(1, 'opponent is required')
    .transform((v) => v.toUpperCase()),
  position: z
    .string()
    .transform((v) => v.toUpperCase())
    .refine((v) => (VALID_POSITIONS as readonly string[]).includes(v), {
      message: `position must be one of ${VALID_POSITIONS.join(', ')}`,
    }),
  roster_positions: z.string().default(''),
  salary: z
    .string()
    .refine((v) => v !== '' && !Number.isNaN(Number(v)), 'salary must be numeric')
    .transform(Number)
    .refine((n) => Number.isInteger(n) && n > 0 && n <= 100000, 'salary must be a positive integer <= 100000'),
  game_info: z.string().default(''),
  start_time: z.string().default(''),
  status: z
    .string()
    .transform((v) => (v ? v.toUpperCase() : 'ACTIVE'))
    .default('ACTIVE'),
});

export type SalaryRow = z.infer<typeof salaryRowSchema>;

export const SALARY_TEMPLATE_HEADERS = [
  'slate_id',
  'slate_name',
  'sport',
  'contest_date',
  'player_id',
  'player_name',
  'team',
  'opponent',
  'position',
  'roster_positions',
  'salary',
  'game_info',
  'start_time',
  'status',
];

export const SALARY_TEMPLATE_SAMPLE_ROW = [
  'DEMO_SLATE_1',
  'Demo Sunday Main Slate',
  'NFL',
  '2026-09-13',
  'DEMO_QB_1',
  'Demo Player QB1',
  'AAA',
  'BBB',
  'QB',
  'QB',
  '7500',
  'AAA@BBB',
  '2026-09-13T13:00:00Z',
  'ACTIVE',
];
