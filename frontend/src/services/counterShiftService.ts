import { api } from "./apiClient";

export type CounterShiftSummary = {
  shiftId: string;
  status: "Open" | "Closed";
  openingCashBalance: number;
  expectedCashTotal: number;
  actualCashTotal: number | null;
  cashVariance: number | null;
  openedByName: string;
  closedByName: string | null;
  openedAt: string;
  closedAt: string | null;
};

export async function getCurrentCounterShift(): Promise<CounterShiftSummary | null> {
  return api.request<CounterShiftSummary | null>("/counter/shifts/current");
}

export async function openCounterShift(openingCashBalance: number): Promise<CounterShiftSummary> {
  return api.request<CounterShiftSummary>("/counter/shifts/open", {
    method: "POST",
    body: JSON.stringify({ openingCashBalance }),
  });
}

export async function closeCounterShift(
  shiftId: string,
  actualCashTotal: number,
  closeNote?: string,
): Promise<CounterShiftSummary> {
  return api.request<CounterShiftSummary>(`/counter/shifts/${encodeURIComponent(shiftId)}/close`, {
    method: "POST",
    body: JSON.stringify({ actualCashTotal, closeNote }),
  });
}

export async function recordCounterAdjustment(
  shiftId: string,
  amount: number,
  reasonCode: string,
  note?: string,
): Promise<void> {
  await api.request(`/counter/shifts/${encodeURIComponent(shiftId)}/adjustments`, {
    method: "POST",
    body: JSON.stringify({ amount, reasonCode, note }),
  });
}
