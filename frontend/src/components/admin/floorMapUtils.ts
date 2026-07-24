import type { AdminTable, AdminTableSessionSummary, Table } from "@cmc/shared-types";

export type FloorMapFilter = "all" | "serving" | "free" | "payment";

export type TableFloorState = "inactive" | "free" | "serving" | "payment";

export type TableFloorRow = {
  table: AdminTable;
  session: AdminTableSessionSummary | null;
  state: TableFloorState;
};

export function getTableFloorState(
  table: Table,
  session: AdminTableSessionSummary | null,
  hasPendingInvoice: boolean,
): TableFloorState {
  if (!table.isActive) return "inactive";
  if (hasPendingInvoice) return "payment";
  if (session && session.status === "Open" && !session.isExpired) return "serving";
  return "free";
}

export function buildTableFloorRows(
  tables: AdminTable[],
  sessions: AdminTableSessionSummary[],
  pendingTableCodes: Set<string>,
): TableFloorRow[] {
  const openByTable = new Map<string, AdminTableSessionSummary>();
  for (const session of sessions) {
    if (session.status !== "Open" || session.isExpired) continue;
    const existing = openByTable.get(session.tableCode);
    if (!existing || new Date(session.openedAt) > new Date(existing.openedAt)) {
      openByTable.set(session.tableCode, session);
    }
  }

  return tables.map((table) => {
    const session = openByTable.get(table.tableCode) ?? null;
    const state = getTableFloorState(table, session, pendingTableCodes.has(table.tableCode));
    return { table, session, state };
  });
}

export function filterFloorRows(rows: TableFloorRow[], filter: FloorMapFilter): TableFloorRow[] {
  if (filter === "all") return rows;
  if (filter === "serving") return rows.filter((row) => row.state === "serving");
  if (filter === "free") return rows.filter((row) => row.state === "free");
  if (filter === "payment") return rows.filter((row) => row.state === "payment");
  return rows;
}
