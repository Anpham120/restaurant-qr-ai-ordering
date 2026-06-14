import type { AdminOrder } from "../types";
import { getKitchenOrders } from "./orderService";

export async function getAdminOrders(): Promise<AdminOrder[]> {
  const orders = await getKitchenOrders();

  return orders.map((order) => ({
    id: order.orderId,
    code: order.orderCode,
    type: order.orderType,
    tableCode: order.tableCode ?? undefined,
    customerName: order.tableCode ? `Bàn ${order.tableCode}` : "Khách pickup",
    status: order.status,
    total: order.totalAmount,
    placedAt: new Intl.DateTimeFormat("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(order.createdAt)),
    paymentStatus:
      order.paymentStatus === "Paid" || order.paymentStatus === "Confirmed" ? "Paid" : "Pending",
    items: order.items.map((item) => ({
      id: item.orderItemId,
      name: item.name,
      quantity: item.quantity,
      status: item.status,
    })),
  }));
}
