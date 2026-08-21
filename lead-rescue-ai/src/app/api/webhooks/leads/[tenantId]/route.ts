import { NextRequest, NextResponse } from "next/server";
import { verifyWebhookSignature } from "@/lib/webhook-signature";
import { leadIntakeSchema, FIRST_RESPONSE_SLA_MS } from "@/lib/lead-intake";
import { createSupabaseServiceRoleClient } from "@/lib/supabase/server";
import { ClaudeFirstResponseGenerator } from "@/lib/ai/generate-first-response";
import { TwilioSmsSender } from "@/lib/sms/sms-sender";
import { respondToNewLead, escalateNewLeadToHumanReview } from "@/lib/lead-response";

const SIGNATURE_HEADER = "x-lead-signature";
const UNIQUE_VIOLATION = "23505";

/**
 * Inbound lead intake: a call-tracking provider or web form posts a new
 * lead here for a specific tenant. Every request must carry a valid
 * HMAC-SHA256 signature (computed over the raw body with that tenant's
 * webhook_signing_secret) in the X-Lead-Signature header, hex-encoded.
 *
 * Uses the service-role client because the caller has no Supabase session —
 * tenant scoping is therefore done explicitly in this handler rather than
 * relying on RLS.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ tenantId: string }> },
) {
  const { tenantId } = await params;

  const rawBody = await request.text();
  const supabase = createSupabaseServiceRoleClient();

  const { data: tenant, error: tenantError } = await supabase
    .from("tenants")
    .select("id, webhook_signing_secret")
    .eq("id", tenantId)
    .maybeSingle();

  if (tenantError) {
    return NextResponse.json({ error: "Lookup failed" }, { status: 500 });
  }
  if (!tenant) {
    return NextResponse.json({ error: "Unknown tenant" }, { status: 404 });
  }

  const signature = request.headers.get(SIGNATURE_HEADER);
  if (!verifyWebhookSignature(rawBody, signature, tenant.webhook_signing_secret)) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  let parsedBody: unknown;
  try {
    parsedBody = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const result = leadIntakeSchema.safeParse(parsedBody);
  if (!result.success) {
    return NextResponse.json(
      { error: "Invalid payload", details: result.error.flatten() },
      { status: 400 },
    );
  }
  const payload = result.data;

  const now = new Date();
  const { data: lead, error: insertError } = await supabase
    .from("leads")
    .insert({
      tenant_id: tenant.id,
      source: payload.source,
      external_ref: payload.external_ref ?? null,
      name: payload.name ?? null,
      phone: payload.phone ?? null,
      email: payload.email ?? null,
      sms_consent: payload.sms_consent,
      sms_consent_at: payload.sms_consent ? now.toISOString() : null,
      first_response_due_at: new Date(now.getTime() + FIRST_RESPONSE_SLA_MS).toISOString(),
    })
    .select("id, status")
    .single();

  if (insertError) {
    // A retried webhook for a lead we've already recorded is not an error —
    // report the existing lead so the sender's retry logic can stand down.
    if (insertError.code === UNIQUE_VIOLATION && payload.external_ref) {
      const { data: existing } = await supabase
        .from("leads")
        .select("id, status")
        .eq("tenant_id", tenant.id)
        .eq("external_ref", payload.external_ref)
        .maybeSingle();

      if (existing) {
        return NextResponse.json({ id: existing.id, status: existing.status, duplicate: true });
      }
    }

    return NextResponse.json({ error: "Could not create lead" }, { status: 500 });
  }

  const { error: eventError } = await supabase.from("lead_events").insert({
    lead_id: lead.id,
    tenant_id: tenant.id,
    actor_type: "system",
    event_type: "lead_created",
    payload: { source: payload.source, external_ref: payload.external_ref ?? null },
  });

  if (eventError) {
    // The lead itself was created successfully; a missing audit row is
    // logged server-side for follow-up rather than failing the webhook
    // (the sender would otherwise retry and create a duplicate lead).
    console.error("Failed to write lead_events row for lead", lead.id, eventError);
  }

  await driveFirstResponse(supabase, {
    id: lead.id,
    tenant_id: tenant.id,
    name: payload.name ?? null,
    phone: payload.phone ?? null,
    source: payload.source,
    sms_consent: payload.sms_consent,
  });

  return NextResponse.json({ id: lead.id, status: lead.status }, { status: 201 });
}

async function driveFirstResponse(
  supabase: ReturnType<typeof createSupabaseServiceRoleClient>,
  lead: Parameters<typeof respondToNewLead>[1],
) {
  const { ANTHROPIC_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER } = process.env;

  if (!ANTHROPIC_API_KEY || !TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_FROM_NUMBER) {
    await escalateNewLeadToHumanReview(supabase, lead, "ai_or_sms_not_configured");
    return;
  }

  await respondToNewLead(
    {
      supabase,
      generator: new ClaudeFirstResponseGenerator(ANTHROPIC_API_KEY),
      sms: new TwilioSmsSender(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER),
    },
    lead,
  );
}
