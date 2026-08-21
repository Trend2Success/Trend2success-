import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database, LeadSource } from "@/lib/supabase/types";
import type { FirstResponseGenerator } from "@/lib/ai/generate-first-response";
import { checkGuardrails } from "@/lib/ai/guardrail-filter";
import type { SmsSender } from "@/lib/sms/sms-sender";
import { assertValidLeadTransition } from "@/lib/lead-state-machine";

export interface NewLead {
  id: string;
  tenant_id: string;
  name: string | null;
  phone: string | null;
  source: LeadSource;
  sms_consent: boolean;
}

export interface RespondToNewLeadDeps {
  supabase: SupabaseClient<Database>;
  generator: FirstResponseGenerator;
  sms: SmsSender;
}

async function logLeadEvent(
  supabase: SupabaseClient<Database>,
  lead: Pick<NewLead, "id" | "tenant_id">,
  eventType: string,
  payload: Record<string, unknown>,
  actorType: "ai" | "system" = "system",
) {
  const { error } = await supabase.from("lead_events").insert({
    lead_id: lead.id,
    tenant_id: lead.tenant_id,
    actor_type: actorType,
    event_type: eventType,
    payload,
  });
  if (error) {
    console.error("Failed to log lead_events row for lead", lead.id, eventType, error);
  }
}

/**
 * Moves a new lead straight to human_review, logging why. Exported on its
 * own so callers that never had a compliant path to an AI response (e.g.
 * the AI/SMS integrations aren't configured yet) don't need to construct a
 * FirstResponseGenerator or SmsSender just to record the escalation.
 */
export async function escalateNewLeadToHumanReview(
  supabase: SupabaseClient<Database>,
  lead: Pick<NewLead, "id" | "tenant_id">,
  reason: string,
  payload: Record<string, unknown> = {},
): Promise<void> {
  await logLeadEvent(supabase, lead, "escalated_to_human_review", { reason, ...payload });
  const { error } = await supabase
    .from("leads")
    .update({ status: assertValidLeadTransition("new", "human_review") })
    .eq("id", lead.id);
  if (error) {
    console.error("Failed to move lead to human_review", lead.id, error);
  }
}

/**
 * Drives a freshly created lead to its first response, per the MVP's
 * non-negotiables: try to get a compliant AI reply out within the SLA, but
 * fall back to human_review — never silence, never an unreviewed message —
 * whenever consent, generation, the guardrail filter, or sending fails.
 * Every branch writes a lead_events row so the outcome is reviewable.
 */
export async function respondToNewLead(deps: RespondToNewLeadDeps, lead: NewLead): Promise<void> {
  const { supabase, generator, sms } = deps;

  const logEvent = (eventType: string, payload: Record<string, unknown>, actorType: "ai" | "system" = "system") =>
    logLeadEvent(supabase, lead, eventType, payload, actorType);

  const escalateToHumanReview = (reason: string, payload: Record<string, unknown> = {}) =>
    escalateNewLeadToHumanReview(supabase, lead, reason, payload);

  if (!lead.sms_consent || !lead.phone) {
    await escalateToHumanReview("no_sms_consent_or_phone");
    return;
  }

  let draft: string;
  try {
    draft = await generator.generate({ name: lead.name, source: lead.source });
  } catch (error) {
    await escalateToHumanReview("ai_generation_failed", { error: String(error) });
    return;
  }

  const violations = checkGuardrails(draft);
  if (violations.length > 0) {
    await logEvent("ai_response_blocked_by_guardrails", { draft, violations }, "ai");
    await escalateToHumanReview("guardrail_violation", { violations });
    return;
  }

  try {
    await sms.send(lead.phone, draft);
  } catch (error) {
    await logEvent("sms_send_failed", { draft, error: String(error) }, "ai");
    await escalateToHumanReview("sms_send_failed", { error: String(error) });
    return;
  }

  const now = new Date().toISOString();
  await logEvent("ai_first_response_sent", { message: draft }, "ai");

  const { error } = await supabase
    .from("leads")
    .update({
      status: assertValidLeadTransition("new", "contacted"),
      first_response_at: now,
    })
    .eq("id", lead.id);
  if (error) {
    console.error("Failed to mark lead as contacted", lead.id, error);
  }
}
