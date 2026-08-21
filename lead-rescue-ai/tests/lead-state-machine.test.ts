import { describe, expect, it } from "vitest";
import {
  LEAD_STATES,
  assertValidLeadTransition,
  canTransitionLeadState,
  isValidLeadState,
  InvalidLeadTransitionError,
} from "../src/lib/lead-state-machine";

describe("lead state machine", () => {
  it("walks the happy path from new to booked", () => {
    expect(canTransitionLeadState("new", "contacted")).toBe(true);
    expect(canTransitionLeadState("contacted", "replied")).toBe(true);
    expect(canTransitionLeadState("replied", "qualified")).toBe(true);
    expect(canTransitionLeadState("qualified", "booked")).toBe(true);
  });

  it("allows human_review from every non-terminal state", () => {
    for (const state of LEAD_STATES) {
      if (state === "lost" || state === "opted_out" || state === "human_review") continue;
      expect(canTransitionLeadState(state, "human_review")).toBe(true);
    }
  });

  it("allows opting out from any active state", () => {
    for (const state of ["new", "contacted", "replied", "qualified"] as const) {
      expect(canTransitionLeadState(state, "opted_out")).toBe(true);
    }
  });

  it("treats lost and opted_out as terminal", () => {
    for (const state of LEAD_STATES) {
      expect(canTransitionLeadState("lost", state)).toBe(false);
      expect(canTransitionLeadState("opted_out", state)).toBe(false);
    }
  });

  it("rejects skipping states, e.g. new straight to booked", () => {
    expect(canTransitionLeadState("new", "booked")).toBe(false);
  });

  it("rejects a no-op transition to the same state", () => {
    expect(canTransitionLeadState("new", "new")).toBe(false);
  });

  it("lets human_review route back into any active state", () => {
    expect(canTransitionLeadState("human_review", "contacted")).toBe(true);
    expect(canTransitionLeadState("human_review", "booked")).toBe(true);
  });

  it("assertValidLeadTransition returns the target state when valid", () => {
    expect(assertValidLeadTransition("new", "contacted")).toBe("contacted");
  });

  it("assertValidLeadTransition throws InvalidLeadTransitionError when invalid", () => {
    expect(() => assertValidLeadTransition("lost", "booked")).toThrow(InvalidLeadTransitionError);
  });

  it("isValidLeadState narrows arbitrary strings", () => {
    expect(isValidLeadState("booked")).toBe(true);
    expect(isValidLeadState("archived")).toBe(false);
  });
});
