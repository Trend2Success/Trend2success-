import { describe, expect, it } from "vitest";
import { signWebhookPayload, verifyWebhookSignature } from "../src/lib/webhook-signature";

describe("verifyWebhookSignature", () => {
  const secret = "test-secret";
  const body = JSON.stringify({ source: "web_form", sms_consent: true });

  it("accepts a correctly signed payload", () => {
    const signature = signWebhookPayload(body, secret);
    expect(verifyWebhookSignature(body, signature, secret)).toBe(true);
  });

  it("rejects a payload signed with the wrong secret", () => {
    const signature = signWebhookPayload(body, "a-different-secret");
    expect(verifyWebhookSignature(body, signature, secret)).toBe(false);
  });

  it("rejects a tampered body even if the signature was valid for the original", () => {
    const signature = signWebhookPayload(body, secret);
    const tamperedBody = JSON.stringify({ source: "web_form", sms_consent: false });
    expect(verifyWebhookSignature(tamperedBody, signature, secret)).toBe(false);
  });

  it("rejects a missing signature header", () => {
    expect(verifyWebhookSignature(body, null, secret)).toBe(false);
  });

  it("rejects a malformed (non-hex) signature header without throwing", () => {
    expect(verifyWebhookSignature(body, "not-hex!!", secret)).toBe(false);
  });

  it("rejects an empty signature header", () => {
    expect(verifyWebhookSignature(body, "", secret)).toBe(false);
  });
});
