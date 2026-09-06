import { z } from 'zod';
import { ColumnSpec } from './columnMap';

export const PROJECTION_COLUMNS: ColumnSpec[] = [
  { key: 'player_id', required: true, aliases: ['id', 'dk_id', 'player id'] },
  { key: 'player_name', required: true, aliases: ['name', 'player'] },
  { key: 'projected_points', required: true, aliases: ['projection', 'proj', 'fpts', 'points'] },
  { key: 'floor', required: false, aliases: ['flr'] },
  { key: 'ceiling', required: false, aliases: ['ceil'] },
  { key: 'standard_deviation', required: false, aliases: ['stdev', 'std_dev', 'sd'] },
  { key: 'projected_ownership', required: false, aliases: ['ownership', 'own', 'proj_own', 'own%'] },
  { key: 'expected_minutes_or_snaps', required: false, aliases: ['snaps', 'minutes', 'expected_snaps'] },
  { key: 'target_share_or_usage', required: false, aliases: ['usage', 'target_share'] },
  { key: 'notes', required: false, aliases: [] },
  { key: 'projection_source', required: false, aliases: ['source'] },
  { key: 'last_updated', required: false, aliases: ['updated', 'updated_at'] },
];

const numeric = (label: string, opts?: { min?: number; max?: number }) =>
  z
    .string()
    .optional()
    .default('')
    .transform((v) => (v === '' ? null : Number(v)))
    .refine((n) => n === null || !Number.isNaN(n), `${label} must be numeric`)
    .refine((n) => n === null || opts?.min === undefined || n >= opts.min, `${label} must be >= ${opts?.min}`)
    .refine((n) => n === null || opts?.max === undefined || n <= opts.max, `${label} must be <= ${opts?.max}`);

export const projectionRowSchema = z
  .object({
    player_id: z.string().min(1, 'player_id is required'),
    player_name: z.string().min(1, 'player_name is required'),
    projected_points: z
      .string()
      .refine((v) => v !== '' && !Number.isNaN(Number(v)), 'projected_points must be numeric')
      .transform(Number)
      .refine((n) => n >= 0 && n <= 100, 'projected_points must be between 0 and 100 (impossible value)'),
    floor: numeric('floor', { min: 0, max: 120 }),
    ceiling: numeric('ceiling', { min: 0, max: 120 }),
    standard_deviation: numeric('standard_deviation', { min: 0, max: 60 }),
    projected_ownership: numeric('projected_ownership', { min: 0, max: 100 }),
    expected_minutes_or_snaps: numeric('expected_minutes_or_snaps', { min: 0, max: 100 }),
    target_share_or_usage: numeric('target_share_or_usage', { min: 0, max: 100 }),
    notes: z.string().default(''),
    projection_source: z.string().default('User Upload'),
    last_updated: z.string().default(''),
  })
  .refine((row) => row.floor === null || row.floor <= row.projected_points + 0.01, {
    message: 'floor cannot exceed projected_points (impossible value)',
    path: ['floor'],
  })
  .refine((row) => row.ceiling === null || row.ceiling >= row.projected_points - 0.01, {
    message: 'ceiling cannot be below projected_points (impossible value)',
    path: ['ceiling'],
  });

export type ProjectionRow = z.infer<typeof projectionRowSchema>;

export const PROJECTION_TEMPLATE_HEADERS = [
  'player_id',
  'player_name',
  'projected_points',
  'floor',
  'ceiling',
  'standard_deviation',
  'projected_ownership',
  'expected_minutes_or_snaps',
  'target_share_or_usage',
  'notes',
  'projection_source',
  'last_updated',
];

export const PROJECTION_TEMPLATE_SAMPLE_ROW = [
  'DEMO_QB_1',
  'Demo Player QB1',
  '19.5',
  '11.0',
  '29.0',
  '6.2',
  '14.5',
  '62',
  '',
  'Consistent floor, upside tied to garbage-time volume',
  'User Upload',
  '2026-09-06T12:00:00Z',
];
