import type { OrderStatus, TableCode } from "./api";

export type CustomerOrderType = "DineIn" | "Pickup" | "DeliveryMock";

export type PaymentMethod = "COD" | "VietQR";

export type OrderItemStatus =
  | "Pending"
  | "Preparing"
  | "Ready"
  | "Served"
  | "Cancelled";

export type DeliveryInfo = {
  recipientName: string;
  phoneNumber: string;
  address: string;
  note?: string;
};

export type CreateOrderItem = {
  menuItemId: string;
  quantity: number;
};

export type CreateOrderRequest = {
  orderType: CustomerOrderType;
  tableCode: TableCode | null;
  paymentMethod: PaymentMethod;
  deliveryInfo: DeliveryInfo | null;
  items: CreateOrderItem[];
};

export type CreateOrderResponse = {
  orderId: string;
  orderCode: string;
  orderType: CustomerOrderType;
  tableCode: TableCode | null;
  status: OrderStatus;
  paymentStatus: "Unpaid" | "Pending" | "Paid" | "Confirmed" | "Failed" | "Cancelled";
  items: Array<{
    orderItemId: string;
    menuItemId: string;
    name: string;
    quantity: number;
    status: OrderItemStatus;
  }>;
};

export type OrderTrackingItem = {
  orderItemId: string;
  menuItemId: string;
  name: string;
  quantity: number;
  status: OrderItemStatus;
  updatedAt: string;
};

export type OrderTrackingOrder = {
  orderId: string;
  orderCode: string;
  orderType: CustomerOrderType;
  tableCode: TableCode | null;
  status: OrderStatus;
  paymentStatus: "Unpaid" | "Pending" | "Paid" | "Confirmed" | "Failed" | "Cancelled";
  createdAt: string;
  updatedAt: string;
  items: OrderTrackingItem[];
};

export type OrderCreatedRealtimeEvent = {
  event: "order.created";
  payload: {
    orderId: string;
    orderCode: string;
    orderType: CustomerOrderType;
    tableCode: TableCode | null;
    status: OrderStatus;
    createdAt: string;
  };
};

export type OrderStatusChangedRealtimeEvent = {
  event: "order.statusChanged";
  payload: {
    orderId: string;
    orderCode: string;
    status: OrderStatus;
    updatedAt: string;
  };
};

export type OrderItemStatusChangedRealtimeEvent = {
  event: "order.itemStatusChanged";
  payload: {
    orderId: string;
    orderCode: string;
    orderItemId: string;
    menuItemName: string;
    status: OrderItemStatus;
    updatedAt: string;
  };
};

export type OrderRealtimeEvent =
  | OrderCreatedRealtimeEvent
  | OrderStatusChangedRealtimeEvent
  | OrderItemStatusChangedRealtimeEvent;
