import { useEffect, useMemo, useState } from "react";
import { getAdminOrders } from "../../services/adminOrderService";
import { getAdminMenuOverview } from "../../services/adminMenuService";
import type { AdminOrder } from "../../types";
import { AdminStatePanel } from "./AdminStatePanel";
import { AdminStatusBadge } from "./AdminStatusBadge";

const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

const shiftChecklist = [
  "Kiểm tra QR của từng bàn trước giờ mở ca.",
  "Xác nhận đơn mới trong 2 phút đầu.",
  "Đẩy món Ready sang staff để tránh nguội món.",
  "Đối soát COD/Paid cuối ca trước khi xuất báo cáo.",
];

export function AdminDashboardOverview() {
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [menuStats, setMenuStats] = useState({ total: 0, available: 0, categories: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getAdminOrders().catch(() => [] as AdminOrder[]),
      getAdminMenuOverview().catch(() => ({ categories: [], items: [] })),
    ])
      .then(([ordersData, menuData]) => {
        setOrders(ordersData);
        setMenuStats({
          total: menuData.items.length,
          available: menuData.items.filter((item) => item.isAvailable).length,
          categories: menuData.categories.length,
        });
      })
      .catch(() => setError("Không tải được dữ liệu tổng quan."))
      .finally(() => setIsLoading(false));
  }, []);

  const summary = useMemo(() => {
    const activeOrders = orders.filter(
      (o) => o.status !== "Completed" && o.status !== "Cancelled",
    );
    const revenue = orders.reduce((total, o) => total + o.total, 0);
    const readyCount = orders.filter((o) => o.status === "Ready").length;
    const unpaidCount = orders.filter(
      (o) => o.paymentStatus !== "Paid" && o.paymentStatus !== "Confirmed",
    ).length;

    return { activeOrders, revenue, readyCount, unpaidCount };
  }, [orders]);

  if (isLoading) {
    return (
      <AdminStatePanel
        title="Đang tải dữ liệu"
        description="Đang kết nối API để lấy thông tin tổng quan."
      />
    );
  }

  if (error) {
    return <AdminStatePanel title="Có lỗi" description={error} />;
  }

  return (
    <div className="ops-dashboard-grid">
      <section className="ops-hero-panel">
        <span className="panel-kicker">Ca vận hành hôm nay</span>
        <h3>Nhà hàng đang hoạt động ổn định</h3>
        <p>
          Dữ liệu thực từ API — {orders.length} đơn tổng cộng,{" "}
          {summary.activeOrders.length} đơn đang xử lý.
        </p>
        <div className="ops-health-row">
          <span>🟢 Menu: {menuStats.available}/{menuStats.total} món</span>
          <span>🟢 {menuStats.categories} danh mục</span>
          <span>🟢 {summary.readyCount} đơn Ready</span>
        </div>
      </section>

      <section className="ops-panel">
        <div className="admin-panel-heading">
          <div>
            <span className="panel-kicker">Đơn đang xử lý</span>
            <h3>Ưu tiên trong ca</h3>
          </div>
          <span className="admin-status admin-status-ready">
            {formatCurrency(summary.revenue)} doanh thu
          </span>
        </div>
        {summary.activeOrders.length === 0 ? (
          <AdminStatePanel
            title="Không có đơn đang xử lý"
            description="Tất cả đơn đã hoàn tất hoặc chưa có đơn mới."
          />
        ) : (
          <div className="table-shell ops-order-table">
            <div className="table-row table-head">
              <span>Đơn</span>
              <span>Bàn/Kênh</span>
              <span>Trạng thái</span>
              <span>Thanh toán</span>
              <span>Tổng</span>
            </div>
            {summary.activeOrders.slice(0, 8).map((order) => (
              <div className="table-row" key={order.id}>
                <strong>{order.code}</strong>
                <span>{order.tableCode ?? order.customerName}</span>
                <AdminStatusBadge status={order.status} />
                <AdminStatusBadge status={order.paymentStatus} />
                <strong>{formatCurrency(order.total)}</strong>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="ops-panel">
        <div className="admin-panel-heading">
          <div>
            <span className="panel-kicker">Thống kê nhanh</span>
            <h3>Chỉ số quan trọng</h3>
          </div>
        </div>
        <div className="ops-feature-list">
          <article className="ops-feature-card">
            <span>Đơn chờ xử lý</span>
            <strong>{summary.activeOrders.length}</strong>
            <p>Chưa hoàn tất hoặc hủy</p>
          </article>
          <article className="ops-feature-card">
            <span>Chưa thanh toán</span>
            <strong>{summary.unpaidCount}</strong>
            <p>COD hoặc VietQR chờ xác nhận</p>
          </article>
          <article className="ops-feature-card">
            <span>Doanh thu</span>
            <strong>{formatCurrency(summary.revenue)}</strong>
            <p>Tổng giá trị các đơn</p>
          </article>
        </div>
      </section>

      <section className="ops-panel">
        <div className="admin-panel-heading">
          <div>
            <span className="panel-kicker">Checklist</span>
            <h3>Trước ca phục vụ</h3>
          </div>
        </div>
        <ol className="ops-checklist">
          {shiftChecklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      </section>
    </div>
  );
}
