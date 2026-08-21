import { describe, expect, it } from "vitest";
import { leadIntakeSchema } from "../src/lib/lead-intake";

describe("leadIntakeSchema", () => {
  it("accepts a minimal valid web form lead", () => {
    const result = leadIntakeSchema.safeParse({ source: "web_form", sms_consent: true });
    expect(result.success).toBe(true);
  });

  it("requires sms_consent to be present and explicit", () => {
    const result = leadIntakeSchema.safeParse({ source: "web_form" });
    expect(result.success).toBe(false);
  });

  it("rejects an unrecognized source", () => {
    const result = leadIntakeSchema.safeParse({ source: "carrier_pigeon", sms_consent: true });
    expect(result.success).toBe(false);
  });

  it("rejects a malformed email", () => {
    const result = leadIntakeSchema.safeParse({
      source: "web_form",
      sms_consent: false,
      email: "not-an-email",
    });
    expect(result.success).toBe(false);
  });

  it("allows sms_consent: false so a lead can be recorded without consent to text", () => {
    const result = leadIntakeSchema.safeParse({ source: "missed_call", sms_consent: false });
    expect(result.success).toBe(true);
  });
});
