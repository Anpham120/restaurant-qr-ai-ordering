import { describe, expect, it } from "vitest";
import { mergeSessionOrdersLoadResults } from "./sessionOrdersLoad";
import type { OrderTrackingOrder, TableInvoice } from "../types";

const invoice: TableInvoice = {
  tableSessionId: "s1",
  invoiceCode: "INV-1",
  tableCode: "T02",
  status: "Confirmed",
  subtotalAmount: 100_000,
  discountAmount: 0,
  totalAmount: 100_000,
  promotionCode: null,
  customerPhoneNumber: null,
  method: "COD",
  orderRounds: [],
  items: [],
  vietQr: null,
};

describe("mergeSessionOrdersLoadResults", () => {
  it("allows settled invoice when session orders endpoint is inactive", () => {
    const result = mergeSessionOrdersLoadResults(
      { status: "rejected", reason: new Error("Table session is closed or expired. Please scan QR again.") },
      { status: "fulfilled", value: invoice },
    );
    expect(result.error).toBeNull();
    expect(result.invoice?.status).toBe("Confirmed");
  });

  it("surfaces error when both invoice and orders fail before settlement", () => {
    const result = mergeSessionOrdersLoadResults(
      { status: "rejected", reason: new Error("closed") },
      { status: "rejected", reason: new Error("closed") },
    );
    expect(result.error).toBeTruthy();
  });

  it("returns orders when both succeed", () => {
    const orders = [{ orderId: "1" }] as unknown as OrderTrackingOrder[];
    const result = mergeSessionOrdersLoadResults(
      { status: "fulfilled", value: orders },
      { status: "fulfilled", value: invoice },
    );
    expect(result.orders).toHaveLength(1);
    expect(result.error).toBeNull();
  });
});
