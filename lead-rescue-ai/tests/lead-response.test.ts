import { describe, expect, it } from "vitest";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "../src/lib/supabase/types";
import { respondToNewLead, escalateNewLeadToHumanReview, type NewLead } from "../src/lib/lead-response";
import type { FirstResponseGenerator } from "../src/lib/ai/generate-first-response";
import type { SmsSender } from "../src/lib/sms/sms-sender";

interface RecordedInsert {
  table: string;
  row: Record<string, unknown>;
}
interface RecordedUpdate {
  table: string;
  patch: Record<string, unknown>;
  id: string;
}

function createFakeSupabase() {
  const inserts: RecordedInsert[] = [];
  const updates: RecordedUpdate[] = [];

  const client = {
    from(table: string) {
      return {
        insert(row: Record<string, unknown>) {
          inserts.push({ table, row });
          return Promise.resolve({ error: null });
        },
        update(patch: Record<string, unknown>) {
          return {
            eq(_column: string, id: string) {
              updates.push({ table, patch, id });
              return Promise.resolve({ error: null });
            },
          };
        },
      };
    },
  };

  return { client: client as unknown as SupabaseClient<Database>, inserts, updates };
}

const baseLead: NewLead = {
  id: "lead-1",
  tenant_id: "tenant-1",
  name: "Jane Homeowner",
  phone: "+15551234567",
  source: "web_form",
  sms_consent: true,
};

class FakeGenerator implements FirstResponseGenerator {
  constructor(private response: string | Error) {}
  async generate(): Promise<string> {
    if (this.response instanceof Error) throw this.response;
    return this.response;
  }
}

class FakeSms implements SmsSender {
  public sent: { to: string; body: string }[] = [];
  constructor(private failure?: Error) {}
  async send(to: string, body: string): Promise<void> {
    if (this.failure) throw this.failure;
    this.sent.push({ to, body });
  }
}

describe("respondToNewLead", () => {
  it("sends a clean AI draft and moves the lead to contacted", async () => {
    const { client, inserts, updates } = createFakeSupabase();
    const sms = new FakeSms();
    const generator = new FakeGenerator("Thanks for reaching out! A team member will follow up shortly.");

    await respondToNewLead({ supabase: client, generator, sms }, baseLead);

    expect(sms.sent).toHaveLength(1);
    expect(sms.sent[0]?.to).toBe(baseLead.phone);

    const leadUpdate = updates.find((u) => u.table === "leads");
    expect(leadUpdate?.patch.status).toBe("contacted");
    expect(leadUpdate?.patch.first_response_at).toBeTypeOf("string");

    const sentEvent = inserts.find((i) => i.row.event_type === "ai_first_response_sent");
    expect(sentEvent).toBeDefined();
    expect(sentEvent?.row.actor_type).toBe("ai");
  });

  it("escalates to human_review without sending when there's no SMS consent", async () => {
    const { client, updates } = createFakeSupabase();
    const sms = new FakeSms();
    const generator = new FakeGenerator("this should never be called");

    await respondToNewLead({ supabase: client, generator, sms }, { ...baseLead, sms_consent: false });

    expect(sms.sent).toHaveLength(0);
    const leadUpdate = updates.find((u) => u.table === "leads");
    expect(leadUpdate?.patch.status).toBe("human_review");
  });

  it("escalates to human_review without sending when there's no phone number", async () => {
    const { client, updates } = createFakeSupabase();
    const sms = new FakeSms();
    const generator = new FakeGenerator("unused");

    await respondToNewLead({ supabase: client, generator, sms }, { ...baseLead, phone: null });

    expect(sms.sent).toHaveLength(0);
    expect(updates.find((u) => u.table === "leads")?.patch.status).toBe("human_review");
  });

  it("escalates to human_review and never sends a message that fails the guardrail filter", async () => {
    const { client, inserts, updates } = createFakeSupabase();
    const sms = new FakeSms();
    const generator = new FakeGenerator("We guarantee we can fix it for $99 — sounds like your compressor is dead.");

    await respondToNewLead({ supabase: client, generator, sms }, baseLead);

    expect(sms.sent).toHaveLength(0);
    expect(updates.find((u) => u.table === "leads")?.patch.status).toBe("human_review");
    const blockedEvent = inserts.find((i) => i.row.event_type === "ai_response_blocked_by_guardrails");
    expect(blockedEvent).toBeDefined();
    expect(blockedEvent?.row.payload).toMatchObject({
      violations: expect.arrayContaining(["price", "availability_commitment", "diagnosis"]),
    });
  });

  it("escalates to human_review when AI generation throws", async () => {
    const { client, updates } = createFakeSupabase();
    const sms = new FakeSms();
    const generator = new FakeGenerator(new Error("model unavailable"));

    await respondToNewLead({ supabase: client, generator, sms }, baseLead);

    expect(sms.sent).toHaveLength(0);
    expect(updates.find((u) => u.table === "leads")?.patch.status).toBe("human_review");
  });

  it("escalates to human_review when sending the SMS fails", async () => {
    const { client, updates } = createFakeSupabase();
    const sms = new FakeSms(new Error("carrier rejected"));
    const generator = new FakeGenerator("A clean, compliant message.");

    await respondToNewLead({ supabase: client, generator, sms }, baseLead);

    expect(updates.find((u) => u.table === "leads")?.patch.status).toBe("human_review");
  });
});

describe("escalateNewLeadToHumanReview", () => {
  it("logs the reason and updates the lead status directly", async () => {
    const { client, inserts, updates } = createFakeSupabase();

    await escalateNewLeadToHumanReview(client, baseLead, "ai_or_sms_not_configured");

    expect(updates.find((u) => u.table === "leads")?.patch.status).toBe("human_review");
    const event = inserts.find((i) => i.row.event_type === "escalated_to_human_review");
    expect(event?.row.payload).toMatchObject({ reason: "ai_or_sms_not_configured" });
  });
});
