import { useEffect, useMemo, useState } from "react";
import type { AdminTableSessionSummary, Order, OrderListResponse } from "@cmc/shared-types";
import { api } from "../../services/apiClient";
import { BarChart3 } from "lucide-react";
import "../operations/operations.css";

const formatVnd = (v: number) => v.toLocaleString("vi-VN") + "đ";

export function AdminDashboardOverview() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [menuCount, setMenuCount] = useState<number>(0);
  const [tableCount, setTableCount] = useState<number>(0);
  const [servingCount, setServingCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [orderData, menuData, tableData, sessionData] = await Promise.all([
          api.orders.list(),
          api.request<unknown[]>("/admin/menu-items"),
          api.tables.listAdmin(),
          api.tables.listAdminSessions("Open"),
        ]);
        setOrders((orderData as OrderListResponse).orders);
        setMenuCount(menuData.length);
        setTableCount(tableData.total);
        const servingTables = new Set(
          sessionData.items
            .filter((s: AdminTableSessionSummary) => !s.isExpired)
            .map((s: AdminTableSessionSummary) => s.tableCode),
        );
        setServingCount(servingTables.size);
      } catch {
        setError("Không tải được dữ liệu tổng quan.");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  const stats = useMemo(() => {
    const today = new Date().toDateString();
    const todayOrders = orders.filter((o) => new Date(o.createdAt).toDateString() === today);
    const revenue = todayOrders
      .filter((o) => o.paymentStatus === "Confirmed" || o.paymentStatus === "Paid")
      .reduce((sum, o) => sum + o.totalAmount, 0);
    const pending = orders.filter((o) => ["Placed", "Confirmed", "Preparing", "Ready", "Served"].includes(o.status)).length;
    const completed = todayOrders.filter((o) => o.status === "Completed").length;
    return { todayOrders: todayOrders.length, revenue, pending, completed, menuCount };
  }, [orders, menuCount]);

  if (isLoading) {
    return <div className="ops-empty"><div className="ops-empty-icon"><BarChart3 aria-hidden="true" /></div>Đang tải...</div>;
  }

  return (
    <div>
      <div className="ops-page-header">
        <h1>Tổng quan</h1>
        <p>Bảng điều khiển quản trị nhà hàng CMC</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}

      <div className="ops-stats">
        <div className="ops-stat-card">
          <div className="ops-stat-label">Đơn hôm nay</div>
          <div className="ops-stat-value">{stats.todayOrders}</div>
          <div className="ops-stat-detail">Tổng đơn trong ngày</div>
        </div>
        <div className="ops-stat-card">
          <div className="ops-stat-label">Doanh thu hôm nay</div>
          <div className="ops-stat-value" style={{ fontSize: 22 }}>{formatVnd(stats.revenue)}</div>
          <div className="ops-stat-detail">Đơn đã xác nhận thanh toán</div>
        </div>
        <div className="ops-stat-card">
          <div className="ops-stat-label">Đang xử lý</div>
          <div className="ops-stat-value">{stats.pending}</div>
          <div className="ops-stat-detail">{"Placed -> Served"}</div>
        </div>
        <div className="ops-stat-card">
          <div className="ops-stat-label">Hoàn tất hôm nay</div>
          <div className="ops-stat-value">{stats.completed}</div>
          <div className="ops-stat-detail">Completed</div>
        </div>
        <div className="ops-stat-card">
          <div className="ops-stat-label">Món trong thực đơn</div>
          <div className="ops-stat-value">{stats.menuCount}</div>
          <div className="ops-stat-detail">Đồng bộ với trang khách hàng</div>
        </div>
        <div className="ops-stat-card">
          <div className="ops-stat-label">Bàn đang phục vụ</div>
          <div className="ops-stat-value">{servingCount}/{tableCount}</div>
          <div className="ops-stat-detail">Phiên bàn đang mở</div>
        </div>
      </div>

      {/* Recent orders table */}
      <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Đơn gần đây</h3>
      {orders.length > 0 ? (
        <table className="ops-table">
          <thead>
            <tr>
              <th>Mã đơn</th>
              <th>Bàn</th>
              <th>Trạng thái</th>
              <th>Thanh toán</th>
              <th>Tổng tiền</th>
              <th>Thời gian</th>
            </tr>
          </thead>
          <tbody>
            {orders.slice(0, 20).map((order) => (
              <tr key={order.orderId}>
                <td><strong>{order.orderCode}</strong></td>
                <td>{order.tableCode ?? "-"}</td>
                <td><span className={`ops-badge ops-badge--${order.status.toLowerCase()}`}>{order.status}</span></td>
                <td>
                  <span className={`ops-badge ops-badge--${order.paymentStatus.toLowerCase()}`}>
                    {order.paymentMethod} · {order.paymentStatus}
                  </span>
                </td>
                <td>{formatVnd(order.totalAmount)}</td>
                <td style={{ fontSize: 12, color: "var(--color-muted)" }}>
                  {new Date(order.createdAt).toLocaleString("vi-VN")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="ops-empty">Chưa có đơn hàng nào</div>
      )}
    </div>
  );
}
