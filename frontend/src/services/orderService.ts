import { menuItems } from "../mocks/menuItems";
import type { CreateOrderRequest, CreateOrderResponse } from "../types";

function waitForMockNetwork() {
  return new Promise((resolve) => window.setTimeout(resolve, 450));
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
