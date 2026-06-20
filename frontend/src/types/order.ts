import type { OrderStatus, TableCode } from "./api";

export type CustomerOrderType = "DineIn" | "Pickup";

export type PaymentMethod = "COD" | "VietQR";
export type PaymentStatus = "Unpaid" | "Pending" | "Paid" | "Confirmed" | "Failed" | "Cancelled";

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
  customerAccessToken?: string | null;
  orderType: CustomerOrderType;
  tableCode: TableCode | null;
  status: OrderStatus;
  paymentStatus: PaymentStatus;
  paymentMethod: PaymentMethod;
  deliveryInfo: DeliveryInfo | null;
  subtotalAmount: number;
  totalAmount: number;
  createdAt: string;
  updatedAt: string;
  items: Array<{
    orderItemId: string;
    menuItemId: string;
    name: string;
    unitPrice: number;
    quantity: number;
    status: OrderItemStatus;
    lineTotal: number;
    updatedAt: string;
  }>;
};

export type OrderTrackingItem = {
  orderItemId: string;
  menuItemId: string;
  name: string;
  unitPrice: number;
  quantity: number;
  status: OrderItemStatus;
  lineTotal: number;
  updatedAt: string;
};

export type OrderTrackingOrder = {
  orderId: string;
  orderCode: string;
  orderType: CustomerOrderType;
  tableCode: TableCode | null;
  status: OrderStatus;
  paymentStatus: PaymentStatus;
  paymentMethod: PaymentMethod;
  deliveryInfo: DeliveryInfo | null;
  subtotalAmount: number;
  totalAmount: number;
  createdAt: string;
  updatedAt: string;
  items: OrderTrackingItem[];
};

export type PaymentTransaction = {
  transactionId: string;
  method: PaymentMethod;
  status: PaymentStatus;
  amount: number;
  provider: string;
  providerTransactionId: string | null;
  note: string | null;
  createdAt: string;
};

export type PaymentResponse = {
  paymentId: string;
  orderCode: string;
  method: PaymentMethod;
  status: PaymentStatus;
  amount: number;
  providerTransactionId: string | null;
  createdAt: string;
  paidAt: string | null;
  updatedAt: string;
  transactions: PaymentTransaction[];
};

export type VietQrPaymentResponse = {
  orderCode: string;
  amount: number;
  transferContent: string;
  bankId: string;
  accountNumber: string;
  accountName: string;
  quickLink: string;
  qrPayload: string;
  qrImageDataUri: string;
  paymentStatus: PaymentStatus;
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
