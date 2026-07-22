import { describe, expect, it } from "vitest";
import type { AdminTableSessionSummary, Table } from "@cmc/shared-types";
import { buildTableFloorRows, filterFloorRows, getTableFloorState } from "./floorMapUtils";

const table = (code: string, active = true): Table => ({
  tableCode: code,
  displayName: `Ban ${code}`,
  isActive: active,
});

const session = (code: string): AdminTableSessionSummary => ({
  sessionId: `sess-${code}`,
  tableCode: code,
  displayName: `Ban ${code}`,
  status: "Open",
  openedAt: "2026-01-01T10:00:00.000Z",
  expiresAt: "2026-01-01T14:00:00.000Z",
  closedAt: null,
  isExpired: false,
  activeOrderCount: 2,
});

describe("floorMapUtils", () => {
  it("marks pending invoice tables as payment state", () => {
    expect(getTableFloorState(table("T01"), session("T01"), true)).toBe("payment");
  });

  it("builds rows and filters by serving/free", () => {
    const rows = buildTableFloorRows(
      [table("T01"), table("T02"), table("T03", false)],
      [session("T01")],
      new Set(["T02"]),
    );
    expect(rows.find((row) => row.table.tableCode === "T01")?.state).toBe("serving");
    expect(rows.find((row) => row.table.tableCode === "T02")?.state).toBe("payment");
    expect(rows.find((row) => row.table.tableCode === "T03")?.state).toBe("inactive");
    expect(filterFloorRows(rows, "free")).toHaveLength(0);
    expect(filterFloorRows(rows, "payment")).toHaveLength(1);
  });
});
