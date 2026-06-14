import { createApiClient } from "@cmc/api-client";
import type { AdminOrder, OrderTrackingOrder } from "../types";

const api = createApiClient({
  getAccessToken: () => localStorage.getItem("cmc.accessToken"),
});

export async function getAdminOrders(): Promise<AdminOrder[]> {
  const response = await api.orders.list();
  return response.orders.map(toAdminOrder);
}

function toAdminOrder(order: OrderTrackingOrder): AdminOrder {
  return {
    id: order.orderId,
    code: order.orderCode,
    type: order.orderType,
    tableCode: order.tableCode ?? undefined,
    customerName:
      order.deliveryInfo?.recipientName ??
      (order.tableCode ? `Bàn ${order.tableCode}` : "Khách mang về"),
    status: order.status,
    total: order.totalAmount,
    placedAt: new Intl.DateTimeFormat("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(order.createdAt)),
    paymentStatus: order.paymentStatus,
    items: order.items.map((item) => ({
      id: item.orderItemId,
      name: item.name,
      quantity: item.quantity,
      status: item.status,
    })),
  };
}
