import { useEffect, useMemo, useState } from "react";
import { StaffOrderBoard } from "../components/staff/StaffOrderBoard";
import { getKitchenOrders, isAwaitingPayment } from "../services/orderService";
import type { OrderTrackingOrder } from "../types";
import { PageShell } from "./PageShell";

export function StaffOrdersPage() {
  const [orders, setOrders] = useState<OrderTrackingOrder[] | null>(null);

  useEffect(() => {
    getKitchenOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  const stats = useMemo(() => {
    if (!orders) {
      return [
        { label: "Món chờ mang ra", value: "…", detail: "Nhận từ bếp" },
        { label: "Đơn chờ thu", value: "…", detail: "COD/VietQR chưa xác nhận" },
        { label: "Đã hoàn tất", value: "…", detail: "Trong danh sách hiện tại" },
      ];
    }
    const ready = orders.filter((order) => order.status === "Ready").length;
    const awaiting = orders.filter(isAwaitingPayment).length;
    const completed = orders.filter((order) => order.status === "Completed").length;
    return [
      { label: "Món chờ mang ra", value: String(ready), detail: "Nhận từ bếp" },
      { label: "Đơn chờ thu", value: String(awaiting), detail: "COD/VietQR chưa xác nhận" },
      { label: "Đã hoàn tất", value: String(completed), detail: "Trong danh sách hiện tại" },
    ];
  }, [orders]);

  return (
    <PageShell
      eyebrow="Staff"
      title="Đơn cần phục vụ"
      description="Bảng theo dõi để nhân viên CMC nhận món từ bếp, phục vụ khách, chuyển thu COD và hoàn tất đơn trong ca."
      variant="staff"
      stats={stats}
    >
      <StaffOrderBoard />
    </PageShell>
  );
}
