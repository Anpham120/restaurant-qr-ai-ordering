import type { AdminOrder } from "../types";

export async function getAdminOrders(): Promise<AdminOrder[]> {
  return [
    {
      id: "ord-001",
      code: "ORDER-001",
      type: "DineIn",
      tableCode: "T-05",
      customerName: "Bàn T-05",
      status: "Placed",
      total: 310000,
      placedAt: "10:24",
      paymentStatus: "Pending",
      items: [
        { id: "oi-001", name: "Gỏi cuốn tôm thịt", quantity: 2, status: "Placed" },
        { id: "oi-002", name: "Trà đào cam sả", quantity: 2, status: "Placed" },
      ],
    },
    {
      id: "ord-002",
      code: "ORDER-002",
      type: "Pickup",
      customerName: "Anh Minh",
      status: "Preparing",
      total: 430000,
      placedAt: "10:42",
      paymentStatus: "Pending",
      items: [
        { id: "oi-003", name: "Bò lúc lắc", quantity: 1, status: "Preparing" },
        { id: "oi-004", name: "Nem rán Hà Nội", quantity: 2, status: "Ready" },
      ],
    },
    {
      id: "ord-003",
      code: "ORDER-003",
      type: "DeliveryMock",
      customerName: "Chị Hạnh",
      status: "Ready",
      total: 565000,
      placedAt: "11:05",
      paymentStatus: "Paid",
      items: [
        { id: "oi-005", name: "Lẩu Thái hải sản", quantity: 1, status: "Ready" },
        { id: "oi-006", name: "Chè khúc bạch", quantity: 2, status: "Ready" },
      ],
    },
  ];
}
