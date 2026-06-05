import { useEffect, useMemo, useState } from "react";
import { getAdminOrders } from "../../services/adminOrderService";
import type { AdminOrder, OrderStatus } from "../../types";
import { AdminStatePanel } from "./AdminStatePanel";
import { AdminStatusBadge } from "./AdminStatusBadge";

const statuses: Array<OrderStatus | "All"> = ["All", "Placed", "Preparing", "Ready"];
const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

export function AdminOrderManager() {
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<OrderStatus | "All">("All");
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminOrders()
      .then((nextOrders) => {
        setOrders(nextOrders);
        setSelectedOrderId(nextOrders[0]?.id ?? null);
      })
      .catch(() => setError("Không tải được danh sách đơn mẫu."))
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

  if (isLoading) {
    return <AdminStatePanel title="Đang tải đơn hàng" description="Chuẩn bị dữ liệu đơn mẫu." />;
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
          <p>Danh sách và chi tiết đơn dùng status contract, sẵn sàng nối service thật.</p>
        </div>
      </section>

      <section className="admin-category-strip" aria-label="Lọc trạng thái đơn">
        {statuses.map((status) => (
          <button
            className={selectedStatus === status ? "admin-chip active" : "admin-chip"}
            key={status}
            type="button"
            onClick={() => setSelectedStatus(status)}
          >
            {status === "All" ? "Tất cả" : status}
          </button>
        ))}
      </section>

      <div className="admin-split-layout orders">
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <div>
              <span className="panel-kicker">Danh sách đơn</span>
              <h3>Ưu tiên xử lý</h3>
            </div>
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
                  <small>{order.placedAt} · {order.type}</small>
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
                  <dd>{selectedOrder.type}</dd>
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
                  Cập nhật trạng thái
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
