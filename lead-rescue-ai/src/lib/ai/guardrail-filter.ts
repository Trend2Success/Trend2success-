export type GuardrailViolation = "price" | "availability_commitment" | "diagnosis";

/**
 * Deterministic backstop for the subset of AI non-negotiables that are
 * reliably detectable in plain text: never quote a price, never commit to a
 * specific appointment time, never diagnose the customer's problem. This is
 * not a substitute for the system prompt in generate-first-response.ts —
 * it exists so a prompt-injection attempt or a model slip-up can't reach
 * the customer unnoticed. A message that trips any of these must never be
 * sent; route the lead to human_review instead.
 */
const PRICE_PATTERNS = [
  /\$\s?\d/, // "$99", "$ 99"
  /\b\d+(\.\d+)?\s*(dollars|usd|bucks)\b/i,
  /\b(price|pricing|quote|cost|estimate|rate|charge|fee)\b/i,
];

const AVAILABILITY_PATTERNS = [
  /\bguarantee/i,
  /\bI(’|')?ll\s+(be there|come|arrive)\b/i,
  /\bwe\s+can\s+(be there|come|arrive|send someone)\b/i,
  // A day-of-week or "today"/"tomorrow" paired with a clock time reads as a
  // committed slot, e.g. "tomorrow at 3pm" or "Monday by 9am".
  /\b(today|tonight|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b[^.!?]{0,20}\b(at|by)\b\s*\d{1,2}(:\d{2})?\s*(am|pm)?\b/i,
];

const DIAGNOSIS_PATTERNS = [
  /\bsounds like\b/i,
  /\bit(’|')?s\s+(probably|likely)\b/i,
  /\b(your|the)\s+(unit|system|compressor|furnace|ac|hvac|heater|pipe|pipes|water heater|boiler)\s+(is|needs|has|are)\b/i,
  /\bdiagnos(e|is|ing|ed)\b/i,
];

function matchesAny(text: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(text));
}

export function checkGuardrails(message: string): GuardrailViolation[] {
  const violations: GuardrailViolation[] = [];

  if (matchesAny(message, PRICE_PATTERNS)) violations.push("price");
  if (matchesAny(message, AVAILABILITY_PATTERNS)) violations.push("availability_commitment");
  if (matchesAny(message, DIAGNOSIS_PATTERNS)) violations.push("diagnosis");

  return violations;
}

export function passesGuardrails(message: string): boolean {
  return checkGuardrails(message).length === 0;
}
