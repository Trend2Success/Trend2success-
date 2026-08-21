import { describe, expect, it } from "vitest";
import { checkGuardrails, passesGuardrails } from "../src/lib/ai/guardrail-filter";

describe("checkGuardrails", () => {
  it("passes a clean acknowledgment message", () => {
    expect(checkGuardrails("Hi Jane, thanks for reaching out about your AC! A team member will follow up shortly to get you scheduled.")).toEqual([]);
    expect(passesGuardrails("Hi Jane, thanks for reaching out! What's the best number to reach you at?")).toBe(true);
  });

  it("flags an explicit dollar amount", () => {
    expect(checkGuardrails("That repair usually runs about $150.")).toContain("price");
  });

  it("flags a spelled-out price", () => {
    expect(checkGuardrails("It's typically around 150 dollars.")).toContain("price");
  });

  it("flags any mention of cost/quote/rate language", () => {
    expect(checkGuardrails("I can get you a quote once we know more.")).toContain("price");
  });

  it("flags a guarantee", () => {
    expect(checkGuardrails("We guarantee same-day service!")).toContain("availability_commitment");
  });

  it("flags a committed appointment slot", () => {
    expect(checkGuardrails("I'll get someone out tomorrow at 3pm.")).toContain("availability_commitment");
  });

  it("flags a first-person promise to show up", () => {
    expect(checkGuardrails("I'll be there within the hour.")).toContain("availability_commitment");
  });

  it("does not flag a plain qualifying question about the customer's own availability", () => {
    expect(checkGuardrails("What time of day usually works best for you?")).toEqual([]);
  });

  it("flags diagnostic language", () => {
    expect(checkGuardrails("Sounds like your compressor is failing.")).toContain("diagnosis");
  });

  it("flags a direct equipment diagnosis", () => {
    expect(checkGuardrails("Your furnace needs a new igniter.")).toContain("diagnosis");
  });

  it("can flag multiple violations in one message", () => {
    const violations = checkGuardrails("Sounds like your AC is broken — we guarantee we can fix it for $99.");
    expect(violations).toEqual(expect.arrayContaining(["price", "availability_commitment", "diagnosis"]));
  });
});
