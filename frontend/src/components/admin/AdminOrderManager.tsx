import { useCallback, useEffect, useMemo, useState } from "react";
import type { Order, OrderListResponse, OrderStatus } from "@cmc/shared-types";
import { confirmOrderPayment, refundOrderPayment } from "../../services/orderService";
import { failOrderPayment } from "../../services/adminOrderService";
import { api } from "../../services/apiClient";
import { Package, RefreshCw, X } from "lucide-react";
import "../operations/operations.css";

const formatVnd = (v: number) => v.toLocaleString("vi-VN") + "đ";
const ALL_STATUSES: OrderStatus[] = ["Placed", "Confirmed", "Preparing", "Ready", "Served", "Completed", "Cancelled"];

export function AdminOrderManager() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterTable, setFilterTable] = useState("");
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [pendingCode, setPendingCode] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.orders.list({
        status: filterStatus || undefined,
        tableCode: filterTable || undefined,
      }) as OrderListResponse;
      setOrders(data.orders);
    } catch {
      setError("Không tải được đơn hàng.");
    } finally {
      setIsLoading(false);
    }
  }, [filterStatus, filterTable]);

  useEffect(() => { setIsLoading(true); load(); }, [load]);

  const stats = useMemo(() => {
    const active = orders.filter((o) => !["Completed", "Cancelled"].includes(o.status)).length;
    const total = orders.reduce((s, o) => s + o.totalAmount, 0);
    return [
      { label: "Tổng đơn", value: String(orders.length), detail: "Trong kết quả filter" },
      { label: "Đang xử lý", value: String(active), detail: "Placed -> Served" },
      { label: "Tổng giá trị", value: formatVnd(total), detail: "Cộng dồn" },
    ];
  }, [orders]);

  async function handleStatusChange(orderCode: string, status: OrderStatus) {
    setPendingCode(orderCode);
    setNotice("");
    try {
      await api.orders.updateStatus(orderCode, status);
      setNotice(`${orderCode} -> ${status}`);
      await load();
    } catch {
      setNotice("Cập nhật thất bại.");
    } finally {
      setPendingCode(null);
    }
  }

  async function handlePaymentAction(orderCode: string, action: "confirm" | "fail" | "refund") {
    setPendingCode(orderCode);
    try {
      if (action === "confirm") await confirmOrderPayment(orderCode, "Admin xác nhận");
      else if (action === "fail") await failOrderPayment(orderCode, "Admin từ chối");
      else await refundOrderPayment(orderCode, "Admin hoàn tiền");
      setNotice(`${orderCode}: ${action}`);
      await load();
    } catch {
      setNotice("Thao tác thanh toán thất bại.");
    } finally {
      setPendingCode(null);
    }
  }

  if (isLoading) return <div className="ops-empty"><div className="ops-empty-icon"><Package aria-hidden="true" /></div>Đang tải...</div>;

  return (
    <div>
      <div className="ops-page-header">
        <h1>Quản lý đơn hàng</h1>
        <p>Xem, lọc, cập nhật trạng thái và thanh toán cho tất cả đơn</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-stats">
        {stats.map((s) => (
          <div className="ops-stat-card" key={s.label}>
            <div className="ops-stat-label">{s.label}</div>
            <div className="ops-stat-value">{s.value}</div>
            <div className="ops-stat-detail">{s.detail}</div>
          </div>
        ))}
      </div>

      <div className="ops-toolbar">
        <select className="ops-form-select" style={{ width: 180 }} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="">Tất cả trạng thái</option>
          {ALL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input className="ops-form-input" placeholder="Mã bàn (vd: T01)" value={filterTable} onChange={(e) => setFilterTable(e.target.value)} style={{ width: 140 }} />
        <button className="ops-btn ops-btn--ghost" onClick={load} type="button"><RefreshCw aria-hidden="true" size={15} /> Làm mới</button>
      </div>

      <table className="ops-table">
        <thead>
          <tr>
            <th>Mã đơn</th>
            <th>Bàn</th>
            <th>Trạng thái</th>
            <th>TT toán</th>
            <th>Tổng tiền</th>
            <th>Thời gian</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.orderId}>
              <td>
                <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => setSelectedOrder(order)} type="button" style={{ fontWeight: 700 }}>
                  {order.orderCode}
                </button>
              </td>
              <td>{order.tableCode ?? "-"}</td>
              <td><span className={`ops-badge ops-badge--${order.status.toLowerCase()}`}>{order.status}</span></td>
              <td>
                <span className={`ops-badge ops-badge--${order.paymentStatus.toLowerCase()}`}>
                  {order.paymentMethod} · {order.paymentStatus}
                </span>
              </td>
              <td>{formatVnd(order.totalAmount)}</td>
              <td style={{ fontSize: 12, color: "var(--color-muted)" }}>{new Date(order.createdAt).toLocaleString("vi-VN")}</td>
              <td>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {order.status === "Placed" ? <button className="ops-btn ops-btn--primary ops-btn--sm" disabled={pendingCode === order.orderCode} onClick={() => handleStatusChange(order.orderCode, "Confirmed")} type="button">Xác nhận</button> : null}
                  {order.status === "Ready" ? <button className="ops-btn ops-btn--success ops-btn--sm" disabled={pendingCode === order.orderCode} onClick={() => handleStatusChange(order.orderCode, "Served")} type="button">Phục vụ</button> : null}
                  {order.status === "Served" && (order.paymentStatus === "Confirmed" || order.paymentStatus === "Paid") ? (
                    <button className="ops-btn ops-btn--success ops-btn--sm" disabled={pendingCode === order.orderCode} onClick={() => handleStatusChange(order.orderCode, "Completed")} type="button">Hoàn tất</button>
                  ) : null}
                  {!["Completed", "Cancelled"].includes(order.status) ? (
                    <button className="ops-btn ops-btn--ghost ops-btn--sm" disabled={pendingCode === order.orderCode} onClick={() => handleStatusChange(order.orderCode, "Cancelled")} type="button">Hủy</button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
          {orders.length === 0 ? <tr><td colSpan={7}><div className="ops-empty">Không có đơn</div></td></tr> : null}
        </tbody>
      </table>

      {/* Detail modal */}
      {selectedOrder ? (
        <div className="ops-modal-overlay" onClick={() => setSelectedOrder(null)}>
          <div className="ops-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ops-modal-header">
              <h2>{selectedOrder.orderCode}</h2>
              <button aria-label="Đóng" className="ops-modal-close" onClick={() => setSelectedOrder(null)} type="button"><X aria-hidden="true" size={18} /></button>
            </div>
            <div className="ops-modal-body">
              <div className="ops-card-meta" style={{ marginBottom: 12, gap: 8 }}>
                <span className={`ops-badge ops-badge--${selectedOrder.status.toLowerCase()}`}>{selectedOrder.status}</span>
                <span className={`ops-badge ops-badge--${selectedOrder.paymentStatus.toLowerCase()}`}>{selectedOrder.paymentMethod} · {selectedOrder.paymentStatus}</span>
                {selectedOrder.tableCode ? <span className="ops-card-table">Bàn {selectedOrder.tableCode}</span> : null}
              </div>

              <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Món ({selectedOrder.items.length})</h4>
              <div className="ops-item-list">
                {selectedOrder.items.map((item) => (
                  <div className="ops-item-row" key={item.orderItemId}>
                    <div className="ops-item-info">
                      <div className="ops-item-name">
                        {item.quantity}× {item.name}
                        <span className={`ops-badge ops-badge--${item.status.toLowerCase()}`}>{item.status}</span>
                      </div>
                      <span className="ops-item-qty">{formatVnd(item.lineTotal)}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 16, padding: 12, background: "var(--color-bg-subtle)", borderRadius: 8, fontSize: 14 }}>
                <strong>Tổng: {formatVnd(selectedOrder.totalAmount)}</strong>
              </div>

              {/* Events */}
              {selectedOrder.events.length > 0 ? (
                <div style={{ marginTop: 16 }}>
                  <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Lịch sử</h4>
                  {selectedOrder.events.map((ev, i) => (
                    <div key={i} style={{ fontSize: 12, color: "var(--color-muted)", marginBottom: 4 }}>
                      <span className={`ops-badge ops-badge--${ev.status.toLowerCase()}`}>{ev.status}</span>
                      {" "}{new Date(ev.createdAt).toLocaleString("vi-VN")}
                      {ev.note ? ` - ${ev.note}` : ""}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
            <div className="ops-modal-footer">
              {(selectedOrder.paymentStatus === "Pending" || selectedOrder.paymentStatus === "Unpaid") ? (
                <>
                  <button className="ops-btn ops-btn--success" disabled={pendingCode === selectedOrder.orderCode} onClick={() => handlePaymentAction(selectedOrder.orderCode, "confirm")} type="button">Xác nhận thu</button>
                  <button className="ops-btn ops-btn--ghost" disabled={pendingCode === selectedOrder.orderCode} onClick={() => handlePaymentAction(selectedOrder.orderCode, "fail")} type="button">Từ chối</button>
                </>
              ) : null}
              {(selectedOrder.paymentStatus === "Confirmed" || selectedOrder.paymentStatus === "Paid") ? (
                <button className="ops-btn ops-btn--danger" disabled={pendingCode === selectedOrder.orderCode} onClick={() => handlePaymentAction(selectedOrder.orderCode, "refund")} type="button">Hoàn tiền</button>
              ) : null}
              <button className="ops-btn ops-btn--ghost" onClick={() => setSelectedOrder(null)} type="button">Đóng</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
