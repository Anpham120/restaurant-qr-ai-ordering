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
    {
      id: "ord-004",
      code: "ORDER-004",
      type: "DineIn",
      tableCode: "T-02",
      customerName: "Bàn T-02",
      status: "Served",
      total: 250000,
      placedAt: "11:18",
      paymentStatus: "Pending",
      items: [
        { id: "oi-007", name: "Phở bò đặc biệt", quantity: 2, status: "Served" },
        { id: "oi-008", name: "Cà phê sữa đá", quantity: 1, status: "Served" },
      ],
    },
    {
      id: "ord-005",
      code: "ORDER-005",
      type: "DeliveryMock",
      customerName: "Anh Quân",
      status: "Delivered",
      total: 185000,
      placedAt: "11:34",
      paymentStatus: "Paid",
      items: [{ id: "oi-009", name: "Tôm rang muối", quantity: 1, status: "Delivered" }],
    },
  ];
}
