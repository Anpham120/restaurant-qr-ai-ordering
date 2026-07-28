import { describe, expect, it } from "vitest";
import {
  buildAssistanceToastHref,
  buildOrderCreatedToastHref,
  buildPaymentRequestedToastHref,
  resolveOpsToastHref,
} from "./opsToastRouting";

describe("opsToastRouting", () => {
  it("drops admin/counter links for kitchen role", () => {
    expect(buildOrderCreatedToastHref("Kitchen", "T01")).toBeUndefined();
    expect(buildPaymentRequestedToastHref("Kitchen", "T01")).toBeUndefined();
    expect(buildAssistanceToastHref("Kitchen")).toBeUndefined();
    expect(resolveOpsToastHref("Kitchen", "/counter?tab=payments")).toBeUndefined();
  });

  it("keeps table order links for admin and counter", () => {
    expect(buildOrderCreatedToastHref("Admin", "T01")).toBe("/tables/T01/orders");
    expect(buildPaymentRequestedToastHref("CounterStaff", "T02")).toBe("/counter?tab=payments&table=T02");
    expect(buildAssistanceToastHref("CounterStaff")).toBe("/counter?tab=assistance");
  });
});
