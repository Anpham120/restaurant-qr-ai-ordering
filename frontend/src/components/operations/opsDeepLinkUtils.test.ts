import { describe, expect, it } from "vitest";
import {
  buildCounterPaymentsLink,
  buildOrdersKanbanLink,
  buildTableOrdersLink,
  matchesTableFilter,
  normalizeTableCode,
} from "./opsDeepLinkUtils";

describe("opsDeepLinkUtils", () => {
  it("normalizes table codes for comparison", () => {
    expect(normalizeTableCode(" t05 ")).toBe("T05");
    expect(normalizeTableCode(null)).toBe("");
  });

  it("matches table filter when filter empty", () => {
    expect(matchesTableFilter("T01", "")).toBe(true);
  });

  it("matches table filter case-insensitively", () => {
    expect(matchesTableFilter("t01", "T01")).toBe(true);
    expect(matchesTableFilter("T02", "T01")).toBe(false);
  });

  it("builds counter payments link with optional table filter", () => {
    expect(buildCounterPaymentsLink()).toBe("/counter?tab=payments");
    expect(buildCounterPaymentsLink(null)).toBe("/counter?tab=payments");
    expect(buildCounterPaymentsLink(" t05 ")).toBe("/counter?tab=payments&table=T05");
  });

  it("builds orders kanban link with optional table filter", () => {
    expect(buildOrdersKanbanLink()).toBe("/orders?tab=kanban");
    expect(buildOrdersKanbanLink("T12")).toBe("/orders?tab=kanban&table=T12");
  });

  it("builds table-scoped orders page link", () => {
    expect(buildTableOrdersLink()).toBe("/tables");
    expect(buildTableOrdersLink(" t01 ")).toBe("/tables/T01/orders");
  });
});
