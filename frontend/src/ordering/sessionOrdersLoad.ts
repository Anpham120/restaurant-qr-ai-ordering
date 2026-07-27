import type { OrderTrackingOrder, PaymentStatus, TableInvoice } from "../types";

export function isSettledInvoiceStatus(status: PaymentStatus | null | undefined): boolean {
  return status === "Confirmed" || status === "Paid";
}

export function mergeSessionOrdersLoadResults(
  ordersResult: PromiseSettledResult<OrderTrackingOrder[]>,
  invoiceResult: PromiseSettledResult<TableInvoice>,
): { orders: OrderTrackingOrder[]; invoice: TableInvoice | null; error: string | null } {
  const invoice = invoiceResult.status === "fulfilled" ? invoiceResult.value : null;
  const orders = ordersResult.status === "fulfilled" ? ordersResult.value : [];

  if (invoiceResult.status === "rejected" && ordersResult.status === "rejected") {
    const cause = invoiceResult.reason;
    return {
      orders: [],
      invoice: null,
      error: cause instanceof Error ? cause.message : "Không thể tải các món đã gọi.",
    };
  }

  if (ordersResult.status === "rejected" && isSettledInvoiceStatus(invoice?.status)) {
    return { orders, invoice, error: null };
  }

  if (ordersResult.status === "rejected") {
    const cause = ordersResult.reason;
    return {
      orders,
      invoice,
      error: cause instanceof Error ? cause.message : "Không thể tải các món đã gọi.",
    };
  }

  if (invoiceResult.status === "rejected") {
    const cause = invoiceResult.reason;
    return {
      orders,
      invoice: null,
      error: cause instanceof Error ? cause.message : "Không thể tải hóa đơn phiên bàn.",
    };
  }

  return { orders, invoice, error: null };
}
