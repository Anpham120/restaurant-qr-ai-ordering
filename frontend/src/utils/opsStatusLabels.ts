import type { OrderStatus } from "../types";
import type { PaymentMethod, PaymentStatus } from "../types/order";

const ORDER_STATUS_VI: Record<string, string> = {
  Draft: "Bản nháp",
  Placed: "Đã gửi",
  Confirmed: "Đã xác nhận",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Đã phục vụ",
  Completed: "Hoàn tất",
  Cancelled: "Đã hủy",
};

const PAYMENT_STATUS_VI: Record<string, string> = {
  NotRequested: "Chưa yêu cầu thu",
  Unpaid: "Chưa thanh toán",
  Pending: "Chờ thu",
  Paid: "Đã thanh toán",
  Confirmed: "Đã xác nhận thu",
  Failed: "Thất bại",
  Cancelled: "Đã hủy",
  Refunded: "Đã hoàn",
};

const PAYMENT_METHOD_VI: Record<string, string> = {
  Unselected: "Chưa chọn",
  COD: "Tiền mặt",
  VietQR: "VietQR",
};

const ITEM_STATUS_VI: Record<string, string> = {
  Pending: "Chờ xác nhận",
  Preparing: "Đang chuẩn bị",
  Ready: "Sẵn sàng phục vụ",
  Served: "Đã phục vụ",
  Cancelled: "Đã hủy",
};

export function labelOrderStatus(status: OrderStatus | string): string {
  return ORDER_STATUS_VI[status] ?? status;
}

export function labelPaymentStatus(status: PaymentStatus | string): string {
  return PAYMENT_STATUS_VI[status] ?? status;
}

export function labelPaymentMethod(method: PaymentMethod | string): string {
  return PAYMENT_METHOD_VI[method] ?? method;
}

export function labelPaymentChip(method: PaymentMethod | string, status: PaymentStatus | string): string {
  return `${labelPaymentMethod(method)} · ${labelPaymentStatus(status)}`;
}

/** Guest item chip: after order is staff-confirmed, Pending means waiting for kitchen — not staff confirm. */
export function labelGuestItemStatus(itemStatus: string, orderStatus: string): string {
  if (
    itemStatus === "Pending" &&
    orderStatus !== "Placed" &&
    orderStatus !== "Draft" &&
    orderStatus !== "Cancelled"
  ) {
    return "Chờ chế biến";
  }
  return ITEM_STATUS_VI[itemStatus] ?? itemStatus;
}
