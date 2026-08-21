import { z } from "zod";

/**
 * Payload shape for the inbound lead webhook. `sms_consent` is required and
 * explicit — no default of `true` — because SMS consent must never be
 * assumed on the AI's or the platform's behalf.
 */
export const leadIntakeSchema = z.object({
  source: z.enum(["missed_call", "web_form", "sms", "manual"]),
  external_ref: z.string().min(1).max(200).optional(),
  name: z.string().min(1).max(200).optional(),
  phone: z.string().min(1).max(32).optional(),
  email: z.string().email().max(320).optional(),
  sms_consent: z.boolean(),
});

export type LeadIntakePayload = z.infer<typeof leadIntakeSchema>;

export const FIRST_RESPONSE_SLA_MS = 60_000;
