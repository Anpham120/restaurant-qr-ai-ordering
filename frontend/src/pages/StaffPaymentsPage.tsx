import { useCallback, useEffect, useMemo, useState } from "react";
import type { Order, RealtimeConnectionStatus } from "@cmc/shared-types";
import {
  confirmOrderPayment,
  getKitchenOrders,
  refundOrderPayment,
} from "../services/orderService";
import { failOrderPayment } from "../services/adminOrderService";
import {
  connectOrderRealtime,
  disconnectOrderRealtime,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
} from "../services/realtimeOrderService";
import { VietQrPaymentModal } from "../components/customer/VietQrPaymentModal";
import "../components/operations/operations.css";

const formatVnd = (v: number) => v.toLocaleString("vi-VN") + "đ";

function isAwaitingPayment(o: Order): boolean {
  if (o.status === "Cancelled") return false;
  const paid = ["Paid", "Confirmed", "Cancelled", "Refunded"];
  if (paid.includes(o.paymentStatus)) return false;
  if (o.paymentStatus === "Pending" || o.paymentStatus === "Failed") return true;
  return o.status === "Served" || o.status === "Completed";
}

function isCollected(o: Order): boolean {
  return o.paymentStatus === "Confirmed" || o.paymentStatus === "Paid" || o.paymentStatus === "Refunded";
}

export function StaffPaymentsPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [qrOrderCode, setQrOrderCode] = useState<string | null>(null);
  const [refundCode, setRefundCode] = useState<string | null>(null);
  const [refundNote, setRefundNote] = useState("");
  const [connectionStatus, setConnectionStatus] = useState<RealtimeConnectionStatus>("disconnected");

  const loadOrders = useCallback(async () => {
    try {
      const data = await getKitchenOrders();
      const list = (data as { orders?: Order[] }).orders ?? (data as unknown as Order[]);
      setOrders(Array.isArray(list) ? list : []);
    } catch {
      setError("Không tải được danh sách thanh toán.");
    }
  }, []);

  useEffect(() => {
    loadOrders().finally(() => setIsLoading(false));
  }, [loadOrders]);

  useEffect(() => {
    const unC = subscribeRealtimeConnection(setConnectionStatus);
    const unR = subscribeOrderRealtime(() => loadOrders());
    void connectOrderRealtime().catch(() => setConnectionStatus("error"));
    return () => { unC(); unR(); void disconnectOrderRealtime(); };
  }, [loadOrders]);

  const awaiting = useMemo(() => orders.filter(isAwaitingPayment), [orders]);
  const collected = useMemo(() => orders.filter(isCollected), [orders]);

  const stats = useMemo(() => {
    const total = awaiting.reduce((sum, o) => sum + o.totalAmount, 0);
    const refunded = collected.filter((o) => o.paymentStatus === "Refunded").length;
    const paid = collected.length - refunded;
    return [
      { label: "Đơn chờ thu", value: String(awaiting.length), detail: "Chưa xác nhận thanh toán" },
      { label: "Tổng cần thu", value: formatVnd(total), detail: "Cộng dồn đơn chờ" },
      { label: "Đã thu / hoàn", value: `${paid} / ${refunded}`, detail: "Confirmed & Refunded" },
    ];
  }, [awaiting, collected]);

  async function runAction(orderCode: string, action: () => Promise<unknown>, msg: string, cb?: () => void) {
    setPendingCode(orderCode);
    setNotice("");
    try {
      await action();
      await loadOrders();
      setNotice(msg);
      cb?.();
    } catch {
      setNotice("Thao tác thất bại. Thử lại.");
    } finally {
      setPendingCode(null);
    }
  }

  if (isLoading) {
    return <div className="ops-empty"><div className="ops-empty-icon">💳</div>Đang tải...</div>;
  }

  return (
    <div>
      <div className="ops-page-header">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1>Thu ngân</h1>
            <p>Xác nhận, từ chối hoặc hoàn tiền cho các đơn tại bàn</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className={`ops-connection ops-connection--${connectionStatus}`}>
              <span className="ops-connection-dot" />
              {connectionStatus === "connected" ? "Đã kết nối" : "Mất kết nối"}
            </span>
            <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={loadOrders} type="button">🔄 Làm mới</button>
          </div>
        </div>
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

      {/* Awaiting payment */}
      {awaiting.length > 0 ? (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Đơn chờ thu ({awaiting.length})</h3>
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))" }}>
            {awaiting.map((order) => (
              <article className={`ops-card ops-card--${order.status.toLowerCase()}`} key={order.orderId}>
                <div className="ops-card-header">
                  <span className="ops-card-code">{order.orderCode}</span>
                  {order.tableCode ? <span className="ops-card-table">Bàn {order.tableCode}</span> : null}
                </div>
                <div className="ops-card-meta">
                  <span className={`ops-badge ops-badge--${order.paymentStatus.toLowerCase()}`}>
                    {order.paymentMethod === "COD" ? "💵 Tiền mặt" : "📱 QR"} · {order.paymentStatus}
                  </span>
                  <strong>{formatVnd(order.totalAmount)}</strong>
                </div>
                <div className="ops-card-items">
                  {order.items.map((item) => (
                    <span key={item.orderItemId} className="ops-card-item-chip">
                      {item.quantity}× {item.name}
                    </span>
                  ))}
                </div>
                <div className="ops-card-actions">
                  <button
                    className="ops-btn ops-btn--success ops-btn--sm"
                    disabled={pendingCode === order.orderCode}
                    onClick={() => runAction(order.orderCode, () => confirmOrderPayment(order.orderCode, "Thu tại bàn"), `Đã xác nhận thu ${order.orderCode}`)}
                    type="button"
                  >
                    ✓ Xác nhận thu
                  </button>
                  <button
                    className="ops-btn ops-btn--ghost ops-btn--sm"
                    disabled={pendingCode === order.orderCode}
                    onClick={() => runAction(order.orderCode, () => failOrderPayment(order.orderCode, "Từ chối tại bàn"), `Đã từ chối ${order.orderCode}`)}
                    type="button"
                  >
                    Từ chối
                  </button>
                  {order.paymentMethod === "VietQR" ? (
                    <button className="ops-btn ops-btn--primary ops-btn--sm" onClick={() => setQrOrderCode(order.orderCode)} type="button">
                      📱 Hiện QR
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : (
        <div className="ops-empty" style={{ padding: 24 }}>Không có đơn chờ thu</div>
      )}

      {/* Collected */}
      {collected.length > 0 ? (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Đã thu & hoàn tiền ({collected.length})</h3>
          <table className="ops-table">
            <thead>
              <tr>
                <th>Mã đơn</th>
                <th>Bàn</th>
                <th>PT</th>
                <th>TT</th>
                <th>Số tiền</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {collected.map((order) => (
                <tr key={order.orderId}>
                  <td><strong>{order.orderCode}</strong></td>
                  <td>{order.tableCode ?? "—"}</td>
                  <td>{order.paymentMethod === "COD" ? "Tiền mặt" : "QR"}</td>
                  <td><span className={`ops-badge ops-badge--${order.paymentStatus.toLowerCase()}`}>{order.paymentStatus}</span></td>
                  <td>{formatVnd(order.totalAmount)}</td>
                  <td>
                    {(order.paymentStatus === "Confirmed" || order.paymentStatus === "Paid") ? (
                      refundCode === order.orderCode ? (
                        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          <input
                            className="ops-form-input"
                            maxLength={500}
                            onChange={(e) => setRefundNote(e.target.value)}
                            placeholder="Lý do hoàn tiền"
                            style={{ width: 160, padding: "4px 8px", fontSize: 12 }}
                            value={refundNote}
                          />
                          <button
                            className="ops-btn ops-btn--danger ops-btn--sm"
                            disabled={pendingCode === order.orderCode}
                            onClick={() => runAction(order.orderCode, () => refundOrderPayment(order.orderCode, refundNote.trim() || undefined), `Hoàn tiền ${order.orderCode}`, () => { setRefundCode(null); setRefundNote(""); })}
                            type="button"
                          >
                            Xác nhận
                          </button>
                          <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => { setRefundCode(null); setRefundNote(""); }} type="button">Hủy</button>
                        </div>
                      ) : (
                        <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => { setRefundCode(order.orderCode); setRefundNote(""); }} type="button">
                          Hoàn tiền
                        </button>
                      )
                    ) : (
                      <span style={{ color: "var(--color-muted)", fontSize: 12 }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* VietQR modal */}
      {qrOrderCode ? (
        <VietQrPaymentModal
          orderCode={qrOrderCode}
          onClose={() => setQrOrderCode(null)}
          onPaymentConfirmed={() => {
            setQrOrderCode(null);
            setNotice("Thanh toán đã xác nhận.");
            loadOrders();
          }}
        />
      ) : null}
    </div>
  );
}
