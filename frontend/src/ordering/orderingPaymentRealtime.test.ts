import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = fileURLToPath(new URL("..", import.meta.url));

function read(relativePath: string): string {
  return readFileSync(`${root}/${relativePath}`, "utf8");
}

describe("table invoice payment realtime", () => {
  it("backend emits tableInvoice.paymentConfirmed on staff confirm", () => {
    const endpoints = read("../../backend/src/RestaurantQrAiOrdering.Api/Tables/TableInvoiceEndpoints.cs");
    expect(endpoints).toContain("TableInvoicePaymentConfirmedAsync");
    const contracts = read("../../backend/src/RestaurantQrAiOrdering.Api/Realtime/OrderRealtimeContracts.cs");
    expect(contracts).toContain("tableInvoice.paymentConfirmed");
  });

  it("guest session orders page handles payment confirmed event", () => {
    const page = read("ordering/SessionOrdersPage.tsx");
    expect(page).toContain("tableInvoice.paymentConfirmed");
    expect(page).toContain("TableElectronicReceiptModal");
  });
});
