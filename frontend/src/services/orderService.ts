import { menuItems } from "../mocks/menuItems";
import { createApiClient } from "@cmc/api-client";
import type {
  CreateOrderRequest,
  CreateOrderResponse,
  OrderItemStatus,
  OrderTrackingOrder,
} from "../types";

const CUSTOMER_ORDER_STORAGE_KEY = "cmc.customer.orders";
const useMockOrders = import.meta.env.VITE_USE_MOCK_ORDER === "true";
const api = createApiClient();

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
        menuItemId: "mi-006",
        name: "Bò lúc lắc",
        quantity: 2,
        status: "Preparing",
        updatedAt: "2026-06-05T08:12:00Z",
      },
      {
        orderItemId: "oi_002",
        menuItemId: "mi-011",
        name: "Trà đào cam sả",
        quantity: 2,
        status: "Ready",
        updatedAt: "2026-06-05T08:14:00Z",
      },
      {
        orderItemId: "oi_003",
        menuItemId: "mi-001",
        name: "Gỏi cuốn tôm thịt",
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
        menuItemId: "mi-005",
        name: "Phở bò đặc biệt",
        quantity: 1,
        status: "Pending",
        updatedAt: "2026-06-05T08:15:00Z",
      },
      {
        orderItemId: "oi_005",
        menuItemId: "mi-003",
        name: "Nem rán Hà Nội",
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
        menuItemId: "mi-008",
        name: "Tôm rang muối",
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

function loadStoredOrders() {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(CUSTOMER_ORDER_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];

    return Array.isArray(parsed) ? (parsed as OrderTrackingOrder[]) : [];
  } catch {
    return [];
  }
}

function saveStoredOrders(orders: OrderTrackingOrder[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(CUSTOMER_ORDER_STORAGE_KEY, JSON.stringify(orders.slice(0, 12)));
}

function saveStoredOrder(order: OrderTrackingOrder) {
  const nextOrders = [
    order,
    ...loadStoredOrders().filter(
      (storedOrder) => storedOrder.orderCode.toLowerCase() !== order.orderCode.toLowerCase(),
    ),
  ];

  saveStoredOrders(nextOrders);
}

function findStoredOrder(orderCode: string) {
  return loadStoredOrders().find(
    (order) => order.orderCode.toLowerCase() === orderCode.toLowerCase(),
  );
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
  if (!useMockOrders) {
    const response = await api.orders.create({
      ...payload,
      items: payload.items.map(item => ({
        ...item,
        menuItemId: item.menuItemId.replace(/^mi-/, "m_"),
      })),
    });
    return response as CreateOrderResponse;
  }
  await waitForMockNetwork();

  const unavailableItem = payload.items
    .map((orderItem) => menuItems.find((item) => item.id === orderItem.menuItemId))
    .find((item) => item && !item.isAvailable);

  if (unavailableItem) {
    throw new Error(`Món ${unavailableItem.name} đang tạm hết.`);
  }

  if (payload.orderType === "DineIn" && !payload.tableCode) {
    throw new Error("Đơn tại bàn cần có mã bàn từ QR.");
  }

  if (payload.orderType === "DeliveryMock" && !payload.deliveryInfo?.address) {
    throw new Error("Đơn giao hàng cần thông tin người nhận và địa chỉ.");
  }

  const now = new Date().toISOString();
  const orderCode = `ORD-${Math.floor(1000 + Math.random() * 9000)}`;
  const orderItems = payload.items.map((orderItem, index) => {
    const menuItem = menuItems.find((item) => item.id === orderItem.menuItemId);

    return {
      orderItemId: `oi_${String(index + 1).padStart(3, "0")}`,
      menuItemId: orderItem.menuItemId,
      name: menuItem?.name ?? orderItem.menuItemId,
      quantity: orderItem.quantity,
      status: "Pending" as const,
      updatedAt: now,
    };
  });
  const response: CreateOrderResponse = {
    orderId: `ord_${Date.now()}`,
    orderCode,
    orderType: payload.orderType,
    tableCode: payload.tableCode,
    status: "Placed",
    paymentStatus: "Unpaid",
    items: orderItems.map(({ updatedAt: _updatedAt, ...item }) => item),
  };

  saveStoredOrder({
    ...response,
    createdAt: now,
    updatedAt: now,
    items: orderItems,
  });

  return response;
}

export async function getKitchenOrders(): Promise<OrderTrackingOrder[]> {
  await waitForMockNetwork();
  return [...loadStoredOrders(), ...mockOrders].map(cloneOrder);
}

export async function getOrderTracking(orderCode: string): Promise<OrderTrackingOrder> {
  if (!useMockOrders) {
    return api.orders.get(orderCode) as Promise<OrderTrackingOrder>;
  }
  await waitForMockNetwork();

  const storedOrder = findStoredOrder(orderCode);
  if (storedOrder) {
    return cloneOrder(storedOrder);
  }

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
  if (!useMockOrders) {
    return api.orders.updateItemStatus(orderCode, orderItemId, status) as Promise<OrderTrackingOrder>;
  }
  await waitForMockNetwork();

  const storedOrders = loadStoredOrders();
  const storedOrderIndex = storedOrders.findIndex(
    (order) => order.orderCode.toLowerCase() === orderCode.toLowerCase(),
  );
  if (storedOrderIndex >= 0) {
    const storedOrder = storedOrders[storedOrderIndex];
    const storedItem = storedOrder.items.find((orderItem) => orderItem.orderItemId === orderItemId);
    if (!storedItem) {
      throw new Error("ORDER_ITEM_NOT_FOUND");
    }

    const updatedAt = new Date().toISOString();
    storedItem.status = status;
    storedItem.updatedAt = updatedAt;
    storedOrder.status = calculateOrderStatus(storedOrder.items);
    storedOrder.updatedAt = updatedAt;
    saveStoredOrders(storedOrders);

    return cloneOrder(storedOrder);
  }

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
