// Local, deterministic "AI-style" rules assistant. This intentionally does
// NOT call any external LLM/API — it is a keyword + regex parser that turns
// a plain-English instruction into a structured, editable proposal for the
// Lineup Builder's optimizer settings. The user must review and click Apply
// before anything is sent to the optimizer. It never claims a lineup will
// win, never suggests chasing losses, and never encourages bigger deposits.

export interface ProposedRulePatch {
  num_lineups?: number;
  min_salary?: number;
  max_salary?: number;
  min_unique_players?: number;
  global_max_exposure_pct?: number; // applied to every player as a default max_exposure
  global_max_ownership?: number;
  stack_rules?: {
    qb_stack_min?: number;
    qb_stack_max?: number;
    bring_back_min?: number;
    allow_rb_with_qb?: boolean;
    allow_dst_vs_offense?: boolean;
  };
  objective_weights?: {
    ownership_penalty?: number;
    ceiling?: number;
    leverage?: number;
  };
}

export interface ParsedRulesResult {
  patch: ProposedRulePatch;
  assumptions: string[];
  clarificationsNeeded: string[];
  matchedPhrases: string[];
}

function first<T>(regex: RegExp, text: string, mapFn: (m: RegExpMatchArray) => T): T | undefined {
  const m = text.match(regex);
  return m ? mapFn(m) : undefined;
}

export function parsePlainEnglishRules(input: string): ParsedRulesResult {
  const text = input.toLowerCase();
  const patch: ProposedRulePatch = {};
  const assumptions: string[] = [];
  const clarifications: string[] = [];
  const matched: string[] = [];

  const numLineups = first(/(\d+)\s*(tournament\s*)?lineups?/i, text, (m) => Number(m[1]));
  if (numLineups) {
    patch.num_lineups = numLineups;
    matched.push(`${numLineups} lineups`);
  }

  const maxExposure = first(/no more than\s*(\d+(?:\.\d+)?)\s*%\s*exposure/i, text, (m) => Number(m[1]));
  if (maxExposure !== undefined) {
    patch.global_max_exposure_pct = maxExposure;
    matched.push(`max ${maxExposure}% exposure per player`);
  }

  const minSalary = first(/(?:at least|minimum of|min)\s*\$?\s*([\d,]+)\s*(?:in\s*)?salary/i, text, (m) =>
    Number(m[1]!.replace(/,/g, ''))
  );
  if (minSalary !== undefined) {
    patch.min_salary = minSalary;
    matched.push(`min salary used $${minSalary.toLocaleString()}`);
  }

  const maxOwnership = first(/(?:max(?:imum)?|no more than)\s*(\d+(?:\.\d+)?)\s*%\s*(?:total\s*)?ownership/i, text, (m) =>
    Number(m[1])
  );
  if (maxOwnership !== undefined) {
    patch.global_max_ownership = maxOwnership;
    matched.push(`max total lineup ownership ${maxOwnership}%`);
  }

  const uniquePlayers = first(/(\d+)\s*unique players?/i, text, (m) => Number(m[1]));
  if (uniquePlayers !== undefined) {
    patch.min_unique_players = uniquePlayers;
    matched.push(`min ${uniquePlayers} unique players between lineups`);
  }

  if (/qb stack/i.test(text) || /stack.*qb/i.test(text)) {
    const stackCount = first(/qb stacks?\s*(?:with)?\s*(\d+)/i, text, (m) => Number(m[1]));
    patch.stack_rules = {
      ...patch.stack_rules,
      qb_stack_min: stackCount ?? 1,
    };
    matched.push('QB stacking requested');
    if (!stackCount) {
      assumptions.push('Assumed "QB stacks" means at least 1 pass-catcher from the QB\'s team (default) — adjust the minimum if you meant more.');
    }
  }

  if (/bring[\s-]?back/i.test(text)) {
    patch.stack_rules = { ...patch.stack_rules, bring_back_min: 1 };
    matched.push('opponent bring-back requested');
  }

  if (/no rb with qb|avoid rb with qb|exclude rb.*qb/i.test(text)) {
    patch.stack_rules = { ...patch.stack_rules, allow_rb_with_qb: false };
    matched.push('disallow RB from same team as QB');
  }

  if (/dst.*(against|vs).*offense|allow dst vs offense/i.test(text)) {
    patch.stack_rules = { ...patch.stack_rules, allow_dst_vs_offense: true };
    matched.push('allow DST against rostered offense');
  } else if (/no dst.*offense|avoid dst.*offense|restrict dst/i.test(text)) {
    patch.stack_rules = { ...patch.stack_rules, allow_dst_vs_offense: false };
    matched.push('restrict DST vs rostered offense');
  }

  if (/reduce exposure to (highly owned|high[\s-]?owned|chalk)/i.test(text)) {
    patch.objective_weights = { ...patch.objective_weights, ownership_penalty: 0.25 };
    matched.push('reduce exposure to highly-owned players');
    assumptions.push(
      'Interpreted "reduce exposure to highly owned RBs" as raising the ownership-penalty weight in the objective (0.25) — this nudges the optimizer away from chalk broadly, it does not hard-exclude specific RBs. Add explicit excludes/exposure caps on the Player Pool page if you want a hard limit on specific players.'
    );
    clarifications.push('Which specific RBs (or an ownership % cutoff) should be capped? The parser applied a general penalty only.');
  }

  if (/cash|double[\s-]?up/i.test(text) && /tournament|gpp/i.test(text)) {
    clarifications.push('Your instruction mentions both cash-game and tournament language — please confirm which contest type this lineup set targets, since their objective weights conflict.');
  }

  if (Object.keys(patch).length === 0) {
    clarifications.push(
      'No recognized rules were found in that instruction. Try phrases like "20 tournament lineups", "QB stacks with 2 pass catchers", "no more than 40% exposure to any player", "at least $49,000 salary used", or "bring-back".'
    );
  }

  return { patch, assumptions, clarificationsNeeded: clarifications, matchedPhrases: matched };
}
