export const LEAD_STATES = [
  "new",
  "contacted",
  "replied",
  "qualified",
  "booked",
  "human_review",
  "lost",
  "opted_out",
] as const;

export type LeadState = (typeof LEAD_STATES)[number];

/**
 * Allowed forward transitions for each state. `human_review` is reachable
 * from every non-terminal state, since a human must be able to take over
 * any conversation immediately. `lost` and `opted_out` are terminal: once a
 * lead lands there, a new lead is created rather than reopening it.
 */
const TRANSITIONS: Record<LeadState, readonly LeadState[]> = {
  new: ["contacted", "human_review", "lost", "opted_out"],
  contacted: ["replied", "human_review", "lost", "opted_out"],
  replied: ["qualified", "human_review", "lost", "opted_out"],
  qualified: ["booked", "human_review", "lost", "opted_out"],
  booked: ["human_review", "lost"],
  human_review: ["contacted", "replied", "qualified", "booked", "lost", "opted_out"],
  lost: [],
  opted_out: [],
};

export function isValidLeadState(value: string): value is LeadState {
  return (LEAD_STATES as readonly string[]).includes(value);
}

export function canTransitionLeadState(from: LeadState, to: LeadState): boolean {
  if (from === to) return false;
  return TRANSITIONS[from].includes(to);
}

export class InvalidLeadTransitionError extends Error {
  constructor(
    public readonly from: LeadState,
    public readonly to: LeadState,
  ) {
    super(`Cannot transition lead from "${from}" to "${to}"`);
    this.name = "InvalidLeadTransitionError";
  }
}

/**
 * Throws if the transition isn't allowed; otherwise returns the target
 * state, so callers can use this inline when building an update payload.
 */
export function assertValidLeadTransition(from: LeadState, to: LeadState): LeadState {
  if (!canTransitionLeadState(from, to)) {
    throw new InvalidLeadTransitionError(from, to);
  }
  return to;
}
