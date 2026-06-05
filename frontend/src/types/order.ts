import type { OrderStatus, TableCode } from "./api";

export type CustomerOrderType = "DineIn" | "Pickup" | "DeliveryMock";

export type PaymentMethod = "COD";

export type OrderItemStatus = "Pending" | "Preparing" | "Ready";

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
  paymentStatus: "Unpaid" | "Paid";
  items: Array<{
    orderItemId: string;
    menuItemId: string;
    name: string;
    quantity: number;
    status: OrderItemStatus;
  }>;
};
