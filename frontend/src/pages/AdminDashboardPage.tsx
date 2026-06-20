import { useEffect, useMemo, useState } from "react";
import { AdminDashboardOverview } from "../components/admin/AdminDashboardOverview";
import { getAdminOrders } from "../services/adminOrderService";
import type { AdminOrder } from "../types";
import { PageShell } from "./PageShell";

const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

export function AdminDashboardPage() {
  const [orders, setOrders] = useState<AdminOrder[] | null>(null);

  useEffect(() => {
    getAdminOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  const stats = useMemo(() => {
    if (!orders) {
      return [
        { label: "Đơn đang xử lý", value: "…", detail: "Chưa hoàn tất hoặc hủy" },
        { label: "Bàn đang phục vụ", value: "…", detail: "Bàn dine-in đang mở" },
        { label: "Giá trị TB/đơn", value: "…", detail: "Trung bình trên tổng đơn" },
      ];
    }
    const active = orders.filter((order) => order.status !== "Completed" && order.status !== "Cancelled");
    const occupiedTables = new Set(active.filter((order) => order.tableCode).map((order) => order.tableCode)).size;
    const avg =
      orders.length === 0 ? 0 : Math.round(orders.reduce((sum, order) => sum + order.total, 0) / orders.length);
    return [
      { label: "Đơn đang xử lý", value: String(active.length), detail: "Chưa hoàn tất hoặc hủy" },
      { label: "Bàn đang phục vụ", value: String(occupiedTables), detail: "Bàn dine-in đang mở" },
      { label: "Giá trị TB/đơn", value: formatCurrency(avg), detail: "Trung bình trên tổng đơn" },
    ];
  }, [orders]);

  return (
    <PageShell
      eyebrow="Admin"
      title="Tổng quan CMC"
      description="Bảng điều khiển theo dõi đơn đang phục vụ, bàn có khách, QR và trạng thái vận hành trong ngày."
      variant="admin"
      stats={stats}
    >
      <AdminDashboardOverview />
    </PageShell>
  );
}
