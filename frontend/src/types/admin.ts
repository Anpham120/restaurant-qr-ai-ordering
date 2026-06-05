import type { OrderStatus, TableCode } from "./api";
import type { MenuItem } from "./menu";

export type AdminMenuCategory = {
  id: string;
  name: string;
  isActive: boolean;
  itemCount: number;
};

export type AdminMenuItem = MenuItem & {
  categoryId: string;
};

export type AdminMenuOverview = {
  categories: AdminMenuCategory[];
  items: AdminMenuItem[];
};

export type AdminOrderType = "DineIn" | "Pickup" | "DeliveryMock";

export type AdminOrderItem = {
  id: string;
  name: string;
  quantity: number;
  note?: string;
  status: OrderStatus;
};

export type AdminOrder = {
  id: string;
  code: string;
  type: AdminOrderType;
  tableCode?: TableCode;
  customerName: string;
  status: OrderStatus;
  total: number;
  placedAt: string;
  paymentStatus: "Pending" | "Paid";
  items: AdminOrderItem[];
};
