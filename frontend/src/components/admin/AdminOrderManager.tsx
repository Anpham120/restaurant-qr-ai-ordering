import { useEffect, useMemo, useState } from "react";
import { getAdminOrders } from "../../services/adminOrderService";
import type { AdminOrder } from "../../types";
import { AdminStatePanel } from "./AdminStatePanel";
import { AdminStatusBadge } from "./AdminStatusBadge";

type OrderFilterStatus = "All" | "Placed" | "Preparing" | "Ready" | "Served" | "Delivered";

const statuses: OrderFilterStatus[] = [
  "All",
  "Placed",
  "Preparing",
  "Ready",
  "Served",
  "Delivered",
];

const statusLabels: Record<OrderFilterStatus, string> = {
  All: "Tất cả",
  Placed: "Mới đặt",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Đã phục vụ",
  Delivered: "Đã giao",
};

const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

export function AdminOrderManager() {
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<OrderFilterStatus>("All");
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminOrders()
      .then((nextOrders) => {
        setOrders(nextOrders);
        setSelectedOrderId(nextOrders[0]?.id ?? null);
      })
      .catch(() => setError("Không tải được danh sách đơn."))
      .finally(() => setIsLoading(false));
  }, []);

  const visibleOrders = useMemo(
    () =>
      selectedStatus === "All"
        ? orders
        : orders.filter((order) => order.status === selectedStatus),
    [orders, selectedStatus],
  );

  const selectedOrder =
    orders.find((order) => order.id === selectedOrderId) ?? visibleOrders[0] ?? orders[0];

  const orderSummary = useMemo(
    () => ({
      ready: orders.filter((order) => order.status === "Ready").length,
      unpaid: orders.filter((order) => order.paymentStatus === "Pending").length,
      revenue: orders.reduce((total, order) => total + order.total, 0),
    }),
    [orders],
  );

  if (isLoading) {
    return (
      <AdminStatePanel
        title="Đang tải đơn hàng"
        description="Đang tải danh sách đơn cho màn điều phối."
      />
    );
  }

  if (error) {
    return <AdminStatePanel title="Có lỗi dữ liệu" description={error} />;
  }

  return (
    <div className="admin-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">Order control</span>
          <h3>{orders.length} đơn đang theo dõi</h3>
          <p>
            Theo dõi danh sách đơn, chi tiết món, trạng thái xử lý và thanh toán
            trong ca vận hành.
          </p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{orderSummary.ready} đơn Ready</span>
          <span>{orderSummary.unpaid} chờ COD</span>
          <span>{formatCurrency(orderSummary.revenue)}</span>
        </div>
      </section>

      <section className="admin-category-strip" aria-label="Lọc trạng thái đơn">
        {statuses.map((status) => {
          const count =
            status === "All"
              ? orders.length
              : orders.filter((order) => order.status === status).length;

          return (
            <button
              className={selectedStatus === status ? "admin-chip active" : "admin-chip"}
              key={status}
              type="button"
              onClick={() => setSelectedStatus(status)}
            >
              {statusLabels[status]} ({count})
            </button>
          );
        })}
      </section>

      <div className="admin-split-layout orders">
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <div>
              <span className="panel-kicker">Danh sách đơn</span>
              <h3>Ưu tiên xử lý</h3>
            </div>
            <span className="admin-status admin-status-placed">Theo ca sáng</span>
          </div>

          {visibleOrders.length === 0 ? (
            <AdminStatePanel
              title="Không có đơn phù hợp"
              description="Thử chọn trạng thái khác để xem danh sách đơn."
            />
          ) : (
            <div className="admin-order-list">
              {visibleOrders.map((order) => (
                <button
                  className={
                    selectedOrder?.id === order.id ? "admin-order-card active" : "admin-order-card"
                  }
                  key={order.id}
                  type="button"
                  onClick={() => setSelectedOrderId(order.id)}
                >
                  <span>{order.code}</span>
                  <strong>{order.tableCode ?? order.customerName}</strong>
                  <small>
                    {order.placedAt} · {formatOrderType(order.type)}
                  </small>
                  <AdminStatusBadge status={order.status} />
                  <b>{formatCurrency(order.total)}</b>
                </button>
              ))}
            </div>
          )}
        </section>

        <aside className="admin-panel admin-order-detail">
          {selectedOrder ? (
            <>
              <div className="admin-detail-heading">
                <div>
                  <span className="panel-kicker">Chi tiết đơn</span>
                  <h3>{selectedOrder.code}</h3>
                </div>
                <AdminStatusBadge status={selectedOrder.status} />
              </div>
              <dl className="admin-detail-grid">
                <div>
                  <dt>Khách/Bàn</dt>
                  <dd>{selectedOrder.tableCode ?? selectedOrder.customerName}</dd>
                </div>
                <div>
                  <dt>Loại đơn</dt>
                  <dd>{formatOrderType(selectedOrder.type)}</dd>
                </div>
                <div>
                  <dt>Thanh toán</dt>
                  <dd>
                    <AdminStatusBadge status={selectedOrder.paymentStatus} />
                  </dd>
                </div>
                <div>
                  <dt>Tổng tiền</dt>
                  <dd>{formatCurrency(selectedOrder.total)}</dd>
                </div>
              </dl>

              <div className="admin-order-items">
                {selectedOrder.items.map((item) => (
                  <article key={item.id}>
                    <div>
                      <strong>{item.name}</strong>
                      <span>x{item.quantity}</span>
                    </div>
                    <AdminStatusBadge status={item.status} />
                    {item.note ? <p>{item.note}</p> : null}
                  </article>
                ))}
              </div>

              <div className="admin-action-row">
                <button className="button primary" type="button">
                  Xác nhận xử lý
                </button>
                <button className="button" type="button">
                  Gửi staff
                </button>
                <button className="button" type="button">
                  Xem phiếu bếp
                </button>
              </div>
            </>
          ) : (
            <AdminStatePanel title="Chưa chọn đơn" description="Chọn một đơn để xem chi tiết." />
          )}
        </aside>
      </div>
    </div>
  );
}

function formatOrderType(type: AdminOrder["type"]) {
  if (type === "DineIn") {
    return "Tại bàn";
  }

  if (type === "Pickup") {
    return "Mang về";
  }

  return "Giao hàng";
}
