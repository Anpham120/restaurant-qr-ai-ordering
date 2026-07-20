import { describe, expect, it } from "vitest";
import {
  mergeOrderItemStatusChanged,
  mergeOrderStatusChanged,
} from "./opsRealtimeMerge";
import type { Order } from "@cmc/shared-types";

const sampleOrder: Order = {
  orderId: "ord_1",
  orderCode: "ORD-1001",
  orderType: "DineIn",
  tableCode: "T01",
  tableSessionId: "sess_1",
  status: "Preparing",
  paymentStatus: "NotRequested",
  paymentMethod: "Unselected",
  subtotalAmount: 100_000,
  discountAmount: 0,
  totalAmount: 100_000,
  createdAt: "2026-07-19T10:00:00.000Z",
  updatedAt: "2026-07-19T10:00:00.000Z",
  items: [{
    orderItemId: "oi_1",
    menuItemId: "m_1",
    name: "Pho",
    unitPrice: 100_000,
    quantity: 1,
    status: "Preparing",
    lineTotal: 100_000,
    updatedAt: "2026-07-19T10:00:00.000Z",
  }],
  events: [],
};

describe("opsRealtimeMerge", () => {
  it("merges order status changes in place", () => {
    const merged = mergeOrderStatusChanged([sampleOrder], {
      orderId: "ord_1",
      orderCode: "ORD-1001",
      status: "Ready",
      updatedAt: "2026-07-19T10:05:00.000Z",
    });
    expect(merged[0]?.status).toBe("Ready");
  });

  it("merges item status changes in place", () => {
    const merged = mergeOrderItemStatusChanged([sampleOrder], {
      orderId: "ord_1",
      orderCode: "ORD-1001",
      orderItemId: "oi_1",
      menuItemName: "Pho",
      status: "Ready",
      updatedAt: "2026-07-19T10:05:00.000Z",
    });
    expect(merged[0]?.items[0]?.status).toBe("Ready");
  });
});
