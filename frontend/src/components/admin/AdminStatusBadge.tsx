import type { AdminOrder, OrderStatus, PaymentStatus } from "../../types";

type AdminBadgeStatus =
  | AdminOrder["status"]
  | OrderStatus
  | PaymentStatus
  | "Available"
  | "Unavailable"
  | "Serving"
  | "Cleaning";

type AdminStatusBadgeProps = {
  status: AdminBadgeStatus;
};

const statusLabels: Partial<Record<AdminBadgeStatus, string>> = {
  Draft: "Nháp",
  Placed: "Mới đặt",
  Confirmed: "Đã xác nhận",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Đã phục vụ",
  Delivering: "Đang giao",
  Delivered: "Đã giao",
  Completed: "Hoàn tất",
  Cancelled: "Đã hủy",
  Available: "Đang bán",
  Unavailable: "Tạm hết",
  Paid: "Đã thanh toán",
  Pending: "Chờ xử lý",
  Unpaid: "Chưa thanh toán",
  Failed: "Thất bại",
  Refunded: "Đã hoàn tiền",
  Serving: "Đang phục vụ",
  Cleaning: "Đang dọn",
};

export function AdminStatusBadge({ status }: AdminStatusBadgeProps) {
  return (
    <span className={`admin-status admin-status-${status.toLowerCase()}`}>
      {statusLabels[status] ?? status}
    </span>
  );
}
