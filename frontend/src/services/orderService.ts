import { menuItems } from "../mocks/menuItems";
import type {
  CreateOrderRequest,
  CreateOrderResponse,
  OrderItemStatus,
  OrderTrackingOrder,
} from "../types";

function waitForMockNetwork() {
  return new Promise((resolve) => window.setTimeout(resolve, 450));
}

const mockOrders: OrderTrackingOrder[] = [
  {
    orderId: "ord_1001",
    orderCode: "ORD-1001",
    orderType: "DineIn",
    tableCode: "T05",
    status: "Preparing",
    paymentStatus: "Unpaid",
    createdAt: "2026-06-05T08:05:00Z",
    updatedAt: "2026-06-05T08:16:00Z",
    items: [
      {
        orderItemId: "oi_001",
        menuItemId: "m_001",
        name: "Com ga xoi mo",
        quantity: 2,
        status: "Preparing",
        updatedAt: "2026-06-05T08:12:00Z",
      },
      {
        orderItemId: "oi_002",
        menuItemId: "m_007",
        name: "Tra dao cam sa",
        quantity: 2,
        status: "Ready",
        updatedAt: "2026-06-05T08:14:00Z",
      },
      {
        orderItemId: "oi_003",
        menuItemId: "m_005",
        name: "Goi cuon tom thit",
        quantity: 1,
        status: "Pending",
        updatedAt: "2026-06-05T08:16:00Z",
      },
    ],
  },
  {
    orderId: "ord_1002",
    orderCode: "ORD-1002",
    orderType: "DineIn",
    tableCode: "T07",
    status: "Placed",
    paymentStatus: "Unpaid",
    createdAt: "2026-06-05T08:09:00Z",
    updatedAt: "2026-06-05T08:15:00Z",
    items: [
      {
        orderItemId: "oi_004",
        menuItemId: "m_002",
        name: "Com suon nuong",
        quantity: 1,
        status: "Pending",
        updatedAt: "2026-06-05T08:15:00Z",
      },
      {
        orderItemId: "oi_005",
        menuItemId: "m_003",
        name: "Pho bo tai",
        quantity: 1,
        status: "Pending",
        updatedAt: "2026-06-05T08:15:00Z",
      },
    ],
  },
  {
    orderId: "ord_1003",
    orderCode: "ORD-1003",
    orderType: "Pickup",
    tableCode: null,
    status: "Ready",
    paymentStatus: "Unpaid",
    createdAt: "2026-06-05T08:02:00Z",
    updatedAt: "2026-06-05T08:18:00Z",
    items: [
      {
        orderItemId: "oi_006",
        menuItemId: "m_006",
        name: "Cha gio hai san",
        quantity: 2,
        status: "Ready",
        updatedAt: "2026-06-05T08:18:00Z",
      },
    ],
  },
];

function cloneOrder(order: OrderTrackingOrder): OrderTrackingOrder {
  return {
    ...order,
    items: order.items.map((item) => ({ ...item })),
  };
}

function findMockOrder(orderCode: string) {
  return mockOrders.find((order) =>
    order.orderCode.toLowerCase() === orderCode.toLowerCase()
  );
}

function calculateOrderStatus(items: OrderTrackingOrder["items"]) {
  if (items.every((item) => item.status === "Ready" || item.status === "Served")) {
    return "Ready" as const;
  }

  if (items.some((item) => item.status === "Preparing" || item.status === "Ready")) {
    return "Preparing" as const;
  }

  return "Placed" as const;
}

export async function createOrder(
  payload: CreateOrderRequest,
): Promise<CreateOrderResponse> {
  await waitForMockNetwork();

  const unavailableItem = payload.items
    .map((orderItem) => menuItems.find((item) => item.id === orderItem.menuItemId))
    .find((item) => item && !item.isAvailable);

  if (unavailableItem) {
    throw new Error(`Mon ${unavailableItem.name} dang tam het.`);
  }

  if (payload.orderType === "DineIn" && !payload.tableCode) {
    throw new Error("Don DineIn can co ma ban tu QR.");
  }

  if (payload.orderType === "DeliveryMock" && !payload.deliveryInfo?.address) {
    throw new Error("DeliveryMock can thong tin nguoi nhan va dia chi.");
  }

  const orderCode = `ORD-${Math.floor(1000 + Math.random() * 9000)}`;

  return {
    orderId: `ord_${Date.now()}`,
    orderCode,
    orderType: payload.orderType,
    tableCode: payload.tableCode,
    status: "Placed",
    paymentStatus: "Unpaid",
    items: payload.items.map((orderItem, index) => {
      const menuItem = menuItems.find((item) => item.id === orderItem.menuItemId);

      return {
        orderItemId: `oi_${String(index + 1).padStart(3, "0")}`,
        menuItemId: orderItem.menuItemId,
        name: menuItem?.name ?? orderItem.menuItemId,
        quantity: orderItem.quantity,
        status: "Pending",
      };
    }),
  };
}

export async function getKitchenOrders(): Promise<OrderTrackingOrder[]> {
  await waitForMockNetwork();
  return mockOrders.map(cloneOrder);
}

export async function getOrderTracking(orderCode: string): Promise<OrderTrackingOrder> {
  await waitForMockNetwork();

  const order = findMockOrder(orderCode);
  if (order) {
    return cloneOrder(order);
  }

  const fallbackOrder = cloneOrder(mockOrders[0]);
  return {
    ...fallbackOrder,
    orderId: `mock_${orderCode.toLowerCase()}`,
    orderCode,
  };
}

export async function updateOrderItemStatus(
  orderCode: string,
  orderItemId: string,
  status: OrderItemStatus,
): Promise<OrderTrackingOrder> {
  await waitForMockNetwork();

  const order = findMockOrder(orderCode);
  if (!order) {
    throw new Error("ORDER_NOT_FOUND");
  }

  const item = order.items.find((orderItem) => orderItem.orderItemId === orderItemId);
  if (!item) {
    throw new Error("ORDER_ITEM_NOT_FOUND");
  }

  const updatedAt = new Date().toISOString();
  item.status = status;
  item.updatedAt = updatedAt;
  order.status = calculateOrderStatus(order.items);
  order.updatedAt = updatedAt;

  return cloneOrder(order);
}
