export function normalizeTableCode(value: string | null | undefined): string {
  return (value ?? "").trim().toUpperCase();
}

export function matchesTableFilter(tableCode: string | null | undefined, filter: string): boolean {
  const normalizedFilter = normalizeTableCode(filter);
  if (!normalizedFilter) return true;
  return normalizeTableCode(tableCode) === normalizedFilter;
}

export function buildCounterPaymentsLink(tableCode?: string | null): string {
  const base = "/counter?tab=payments";
  const normalized = normalizeTableCode(tableCode);
  return normalized ? `${base}&table=${encodeURIComponent(normalized)}` : base;
}

export function buildOrdersKanbanLink(tableCode?: string | null): string {
  const base = "/orders?tab=kanban";
  const normalized = normalizeTableCode(tableCode);
  return normalized ? `${base}&table=${encodeURIComponent(normalized)}` : base;
}
