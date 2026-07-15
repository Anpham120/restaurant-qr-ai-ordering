import { describe, expect, it } from "vitest";
import { deriveSessionHubState, getSessionResumeDestination } from "./sessionResumeState";

describe("smart table-session resume state", () => {
  it.each([
    ["New", "/table-session/session%2F1/menu"],
    ["CartPending", "/table-session/session%2F1/cart"],
    ["OrderInProgress", "/table-session/session%2F1/orders"],
    ["ReadyForPayment", "/table-session/session%2F1/orders?focus=invoice"],
    ["PaymentPending", "/table-session/session%2F1/orders?focus=invoice"],
    ["Paid", "/table-session/session%2F1/orders?focus=invoice"],
  ] as const)("routes %s to its canonical destination", (state, expected) => {
    expect(getSessionResumeDestination("session/1", state)).toBe(expected);
  });

  it("uses payment precedence and ignores cancelled orders", () => {
    expect(deriveSessionHubState(["Cancelled"], null)).toBe("New");
    expect(deriveSessionHubState(["Served", "Completed"], "Failed")).toBe("ReadyForPayment");
    expect(deriveSessionHubState(["Served", "Ready"], null)).toBe("OrderInProgress");
    expect(deriveSessionHubState(["Preparing"], "Pending")).toBe("PaymentPending");
    expect(deriveSessionHubState(["Preparing"], "Confirmed")).toBe("Paid");
  });
});
