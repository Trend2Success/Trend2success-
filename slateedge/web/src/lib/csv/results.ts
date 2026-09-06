import { z } from 'zod';
import { ColumnSpec } from './columnMap';

export const RESULTS_COLUMNS: ColumnSpec[] = [
  { key: 'slate_id', required: true, aliases: ['slateid'] },
  { key: 'contest_name', required: true, aliases: ['contest'] },
  { key: 'contest_type', required: true, aliases: ['type'] },
  { key: 'field_size', required: false, aliases: ['entries_total', 'field size'] },
  { key: 'entry_fee', required: true, aliases: ['buy_in', 'entry fee'] },
  { key: 'number_of_entries', required: true, aliases: ['entries', 'num_entries'] },
  { key: 'total_entry_fees', required: false, aliases: ['total fees'] },
  { key: 'total_winnings', required: false, aliases: ['winnings', 'payout'] },
  { key: 'net_profit_loss', required: false, aliases: ['net', 'profit_loss', 'pnl'] },
  { key: 'lineup_id', required: false, aliases: [] },
  { key: 'final_rank', required: false, aliases: ['rank'] },
  { key: 'lineup_points', required: false, aliases: ['points', 'score'] },
  { key: 'cash_line', required: false, aliases: [] },
  { key: 'top_one_percent_line', required: false, aliases: ['top1pct', 'top_1_percent_line'] },
  { key: 'notes', required: false, aliases: [] },
];

const money = (label: string) =>
  z
    .string()
    .refine((v) => v !== '' && !Number.isNaN(Number(v)), `${label} must be numeric`)
    .transform(Number);

const optionalNumber = (label: string) =>
  z
    .string()
    .optional()
    .default('')
    .transform((v) => (v === '' ? null : Number(v)))
    .refine((n) => n === null || !Number.isNaN(n), `${label} must be numeric`);

export const resultsRowSchema = z.object({
  slate_id: z.string().min(1, 'slate_id is required'),
  contest_name: z.string().min(1, 'contest_name is required'),
  contest_type: z.string().min(1, 'contest_type is required'),
  field_size: optionalNumber('field_size'),
  entry_fee: money('entry_fee'),
  number_of_entries: money('number_of_entries').refine((n) => Number.isInteger(n) && n >= 0, 'number_of_entries must be a non-negative integer'),
  total_entry_fees: optionalNumber('total_entry_fees'),
  total_winnings: optionalNumber('total_winnings'),
  net_profit_loss: optionalNumber('net_profit_loss'),
  lineup_id: z.string().default(''),
  final_rank: optionalNumber('final_rank'),
  lineup_points: optionalNumber('lineup_points'),
  cash_line: optionalNumber('cash_line'),
  top_one_percent_line: optionalNumber('top_one_percent_line'),
  notes: z.string().default(''),
});

export type ResultsRow = z.infer<typeof resultsRowSchema>;

export const RESULTS_TEMPLATE_HEADERS = [
  'slate_id',
  'contest_name',
  'contest_type',
  'field_size',
  'entry_fee',
  'number_of_entries',
  'total_entry_fees',
  'total_winnings',
  'net_profit_loss',
  'lineup_id',
  'final_rank',
  'lineup_points',
  'cash_line',
  'top_one_percent_line',
  'notes',
];

export const RESULTS_TEMPLATE_SAMPLE_ROW = [
  'DEMO_SLATE_1',
  'Demo $5 Tournament',
  'GPP',
  '11000',
  '5',
  '3',
  '15',
  '0',
  '-15',
  '',
  '48210',
  '134.6',
  '135.2',
  '160.1',
  'Missed cash line narrowly',
];
