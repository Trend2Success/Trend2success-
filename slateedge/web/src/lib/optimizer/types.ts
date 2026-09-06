// Shared request/response types for the SlateEdge Python analytics service
// (slateedge/optimizer-service). Keep in sync with that service's Pydantic models.

export interface OptimizerPlayerInput {
  player_id: string;
  name: string;
  team: string;
  opponent: string;
  position: 'QB' | 'RB' | 'WR' | 'TE' | 'DST';
  salary: number;
  projection: number;
  ceiling: number;
  floor: number;
  ownership: number;
  leverage: number;
  game_id: string;
  locked: boolean;
  excluded: boolean;
}

export interface GroupRule {
  type: 'at_least' | 'at_most' | 'exactly' | 'if_then' | 'exclude_together';
  player_ids: string[];
  count?: number;
  if_player_id?: string;
  then_player_id?: string;
}

export interface StackRules {
  qb_stack_min: number;
  qb_stack_max: number;
  bring_back_min: number;
  allow_rb_with_qb: boolean;
  allow_dst_vs_offense: boolean;
}

export interface ObjectiveWeights {
  projection: number;
  ceiling: number;
  leverage: number;
  ownership_penalty: number;
}

export interface OptimizeRequest {
  players: OptimizerPlayerInput[];
  roster_slots: string[];
  flex_positions: string[];
  salary_cap: number;
  num_lineups: number;
  min_salary: number;
  max_salary: number;
  min_unique_players: number;
  max_exposure: Record<string, number>;
  min_exposure: Record<string, number>;
  global_max_ownership: number | null;
  min_total_projection: number | null;
  min_total_ceiling: number | null;
  max_players_per_team: number;
  min_players_per_game: number | null;
  max_players_per_game: number | null;
  locked_player_ids: string[];
  excluded_player_ids: string[];
  groups: GroupRule[];
  objective_weights: ObjectiveWeights;
  stack_rules: StackRules;
  random_seed: number | null;
  reproducible: boolean;
}

export interface OptimizedLineup {
  lineup_id: string;
  players: string[];
  roster: Record<string, string>;
  salary_used: number;
  total_projection: number;
  total_ceiling: number;
  total_ownership: number;
  leverage_score: number;
  model_score: number;
  stack_summary: string;
}

export interface OptimizeResponse {
  lineups: OptimizedLineup[];
  warnings: string[];
  settings_version: string;
  seed_used: number | null;
}

export interface SimulationPlayerInput {
  player_id: string;
  name: string;
  position: string;
  team: string;
  game_id: string;
  mean: number;
  stdev: number;
}

export interface CorrelationPair {
  player_id_a: string;
  player_id_b: string;
  rho: number;
}

export interface DefaultCorrelationRules {
  qb_own_pass_catcher: number;
  same_game_offense: number;
  dst_vs_opp_offense: number;
}

export interface SimulateRequest {
  players: SimulationPlayerInput[];
  distribution: 'truncated_normal' | 'lognormal';
  num_simulations: number;
  correlations: CorrelationPair[];
  default_correlation_rules: DefaultCorrelationRules;
  lineups: { lineup_id: string; player_ids: string[]; ownership_sum: number }[];
  threshold: number | null;
  random_seed: number | null;
}

export interface PlayerSimStats {
  player_id: string;
  mean: number;
  median: number;
  p75: number;
  p90: number;
  prob_exceeds_threshold: number | null;
}

export interface LineupSimStats {
  lineup_id: string;
  mean: number;
  median: number;
  p75: number;
  p90: number;
  duplication_risk_proxy: number;
}

export interface SimulateResponse {
  player_stats: PlayerSimStats[];
  lineup_stats: LineupSimStats[];
  num_simulations: number;
  distribution: string;
  seed_used: number | null;
}

export const DEFAULT_OBJECTIVE_WEIGHTS: ObjectiveWeights = {
  projection: 1,
  ceiling: 0,
  leverage: 0,
  ownership_penalty: 0,
};

export const DEFAULT_STACK_RULES: StackRules = {
  qb_stack_min: 0,
  qb_stack_max: 3,
  bring_back_min: 0,
  allow_rb_with_qb: true,
  allow_dst_vs_offense: false,
};

export const DEFAULT_ROSTER_SLOTS = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST'];
export const DEFAULT_FLEX_POSITIONS = ['RB', 'WR', 'TE'];
export const DEFAULT_SALARY_CAP = 50000;

export interface LineupPreset {
  name: string;
  description: string;
  num_lineups: number;
  max_exposure_default: number;
  min_unique_players: number;
  objective_weights: ObjectiveWeights;
  stack_rules: StackRules;
  global_max_ownership: number | null;
}

export const LINEUP_PRESETS: LineupPreset[] = [
  {
    name: 'Cash Conservative',
    description: 'Starting point for cash games: prioritizes floor-safe projection, minimal leverage/ownership penalty, low lineup count.',
    num_lineups: 3,
    max_exposure_default: 1,
    min_unique_players: 0,
    objective_weights: { projection: 1, ceiling: 0.1, leverage: 0, ownership_penalty: 0 },
    stack_rules: { qb_stack_min: 0, qb_stack_max: 2, bring_back_min: 0, allow_rb_with_qb: true, allow_dst_vs_offense: true },
    global_max_ownership: null,
  },
  {
    name: 'Single-Entry GPP',
    description: 'Starting point for single-entry tournaments: one lineup, moderate ceiling/leverage weight.',
    num_lineups: 1,
    max_exposure_default: 1,
    min_unique_players: 0,
    objective_weights: { projection: 0.6, ceiling: 0.3, leverage: 0.1, ownership_penalty: 0.1 },
    stack_rules: { qb_stack_min: 1, qb_stack_max: 2, bring_back_min: 0, allow_rb_with_qb: true, allow_dst_vs_offense: false },
    global_max_ownership: null,
  },
  {
    name: '3-Max GPP',
    description: 'Starting point for 3-max tournaments: some diversification across 3 lineups with ceiling emphasis.',
    num_lineups: 3,
    max_exposure_default: 0.67,
    min_unique_players: 2,
    objective_weights: { projection: 0.5, ceiling: 0.35, leverage: 0.15, ownership_penalty: 0.15 },
    stack_rules: { qb_stack_min: 1, qb_stack_max: 3, bring_back_min: 0, allow_rb_with_qb: true, allow_dst_vs_offense: false },
    global_max_ownership: null,
  },
  {
    name: '20-Max GPP',
    description: 'Starting point for high-volume tournaments: many diversified lineups, leverage- and ownership-penalty weighted.',
    num_lineups: 20,
    max_exposure_default: 0.5,
    min_unique_players: 3,
    objective_weights: { projection: 0.4, ceiling: 0.35, leverage: 0.15, ownership_penalty: 0.1 },
    stack_rules: { qb_stack_min: 1, qb_stack_max: 3, bring_back_min: 1, allow_rb_with_qb: true, allow_dst_vs_offense: false },
    global_max_ownership: null,
  },
];
