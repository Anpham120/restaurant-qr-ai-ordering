import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { OrderTrackingOrder } from "../types";
import { getTableSessionOrders } from "../services/orderService";
import { useOrderingSession } from "./OrderingSessionProvider";

const itemStatusLabel: Record<string, string> = {
  Pending: "Chờ xác nhận",
  Preparing: "Đang chuẩn bị",
  Ready: "Sẵn sàng phục vụ",
  Served: "Đã phục vụ",
  Cancelled: "Đã hủy",
};

const formatVnd = (amount: number) => `${amount.toLocaleString("vi-VN")}đ`;

export function SessionOrdersPage() {
  const { context } = useOrderingSession();
  const [orders, setOrders] = useState<OrderTrackingOrder[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadOrders() {
    setLoading(true);
    setError("");
    try {
      const nextOrders = await getTableSessionOrders(context.sessionId, context.sessionToken);
      setOrders(nextOrders);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể tải các món đã gọi.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadOrders(); }, [context.sessionId, context.sessionToken]);

  if (loading) return <section className="ordering-page"><p>Đang tải các lần gọi món…</p></section>;

  return (
    <section className="ordering-page" aria-labelledby="session-orders-title">
      <header className="ordering-page-heading">
        <div><p>Phiên bàn {context.tableCode}</p><h1 id="session-orders-title">Món đã gọi</h1></div>
        <button type="button" onClick={() => void loadOrders()}>Làm mới</button>
      </header>
      {error ? <div className="ordering-inline-error" role="alert"><p>{error}</p><button type="button" onClick={() => void loadOrders()}>Thử lại</button></div> : null}
      {!error && orders.length === 0 ? (
        <div className="ordering-empty"><p>Bàn chưa có lần gọi món nào trong phiên này.</p><Link to="../menu">Quay lại thực đơn</Link></div>
      ) : null}
      <div className="ordering-orders-list">
        {orders.map((order) => (
          <article className="ordering-order-card" key={order.orderId}>
            <header>
              <div><strong>{order.orderCode}</strong><span>{new Date(order.createdAt).toLocaleString("vi-VN")}</span></div>
              <Link to={order.orderCode}>Chi tiết</Link>
            </header>
            <ul>
              {order.items.map((item) => (
                <li key={item.orderItemId}><span>{item.quantity}× {item.name}</span><em>{itemStatusLabel[item.status] ?? item.status}</em></li>
              ))}
            </ul>
            <footer><span>Chế biến: {order.status}</span><span>Thanh toán: {order.paymentStatus}</span><strong>{formatVnd(order.totalAmount)}</strong></footer>
          </article>
        ))}
      </div>
    </section>
  );
}
