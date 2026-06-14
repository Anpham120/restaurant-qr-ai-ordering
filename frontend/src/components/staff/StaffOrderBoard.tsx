import { useEffect, useMemo, useState } from "react";
import {
  confirmOrderPayment,
  getKitchenOrders,
  updateOrderItemStatus,
  updateOrderStatus,
} from "../../services/orderService";
import type { OrderTrackingOrder } from "../../types";
import { AdminStatePanel } from "../admin/AdminStatePanel";

type StaffLane = "Ready" | "Served" | "PaymentPending" | "Completed";

const lanes: Array<{
  status: StaffLane;
  title: string;
  hint: string;
}> = [
  { status: "Ready", title: "Sẵn sàng phục vụ", hint: "Món bếp đã hoàn thành và cần mang ra." },
  { status: "Served", title: "Đã phục vụ", hint: "Đơn đã ra bàn, chờ thanh toán hoặc hoàn tất." },
  { status: "PaymentPending", title: "Chờ xác nhận thanh toán", hint: "COD/VietQR cần staff xác nhận." },
  { status: "Completed", title: "Hoàn tất", hint: "Đơn đã kết thúc trong ca." },
];

export function StaffOrderBoard() {
  const [orders, setOrders] = useState<OrderTrackingOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyOrderCode, setBusyOrderCode] = useState<string | null>(null);

  useEffect(() => {
    refreshOrders();
  }, []);

  async function refreshOrders() {
    setError("");
    setIsLoading(true);

    try {
      setOrders(await getKitchenOrders());
    } catch {
      setError("Không tải được danh sách đơn từ backend.");
    } finally {
      setIsLoading(false);
    }
  }

  const summary = useMemo(
    () => ({
      ready: orders.filter((order) => getLane(order) === "Ready").length,
      payment: orders.filter((order) => getLane(order) === "PaymentPending").length,
      completed: orders.filter((order) => getLane(order) === "Completed").length,
    }),
    [orders],
  );

  async function markServed(order: OrderTrackingOrder) {
    setBusyOrderCode(order.orderCode);
    setError("");

    try {
      for (const item of order.items.filter((nextItem) => nextItem.status === "Ready")) {
        await updateOrderItemStatus(order.orderCode, item.orderItemId, "Served");
      }

      const updatedOrder = await updateOrderStatus(order.orderCode, "Served");
      setOrders((current) => replaceOrder(current, updatedOrder));
    } catch {
      setError("Không thể chuyển đơn sang trạng thái đã phục vụ.");
    } finally {
      setBusyOrderCode(null);
    }
  }

  async function confirmPayment(order: OrderTrackingOrder) {
    setBusyOrderCode(order.orderCode);
    setError("");

    try {
      await confirmOrderPayment(order.orderCode);
      const updatedOrder = await updateOrderStatus(order.orderCode, "Completed");
      setOrders((current) => replaceOrder(current, updatedOrder));
    } catch {
      setError("Không thể xác nhận thanh toán cho đơn này.");
    } finally {
      setBusyOrderCode(null);
    }
  }

  if (isLoading) {
    return (
      <AdminStatePanel
        title="Đang tải đơn vận hành"
        description="Staff board đang lấy dữ liệu đơn hàng thật từ backend."
      />
    );
  }

  if (error && orders.length === 0) {
    return <AdminStatePanel title="Không tải được đơn" description={error} />;
  }

  return (
    <div className="staff-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">Staff station</span>
          <h3>Luồng phục vụ theo backend</h3>
          <p>
            Board này đọc đơn từ API thật, chuyển món Ready sang Served và xác nhận thanh toán
            COD/VietQR bằng endpoint vận hành.
          </p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{summary.ready} đơn cần mang ra</span>
          <span>{summary.payment} đơn chờ thanh toán</span>
          <span>{summary.completed} hoàn tất</span>
        </div>
        <button className="button" onClick={refreshOrders} type="button">
          Tải lại
        </button>
      </section>

      {error ? <p className="realtime-error">{error}</p> : null}

      <section className="staff-board" aria-label="Staff order board">
        {lanes.map((lane) => {
          const laneOrders = orders.filter((order) => getLane(order) === lane.status);

          return (
            <article className="staff-lane" key={lane.status}>
              <div className="realtime-lane-heading">
                <div>
                  <h3>{lane.title}</h3>
                  <p>{lane.hint}</p>
                </div>
                <span>{laneOrders.length}</span>
              </div>

              {laneOrders.length === 0 ? (
                <p className="realtime-empty">Chưa có đơn trong cột này.</p>
              ) : (
                laneOrders.map((order) => (
                  <div className="staff-ticket" key={order.orderId}>
                    <div className="staff-ticket-meta">
                      <span>{order.orderCode}</span>
                      <strong>{order.tableCode ? `Bàn ${order.tableCode}` : "Pickup"}</strong>
                      <small>{formatPayment(order)}</small>
                    </div>
                    <ul>
                      {order.items.map((item) => (
                        <li key={item.orderItemId}>
                          <span>{item.name}</span>
                          <b>
                            x{item.quantity} - {item.status}
                          </b>
                        </li>
                      ))}
                    </ul>
                    <p>Cập nhật: {formatTime(order.updatedAt)}</p>
                    <div className="staff-action-row">
                      {getLane(order) === "Ready" ? (
                        <button
                          className="button primary"
                          disabled={busyOrderCode === order.orderCode}
                          onClick={() => markServed(order)}
                          type="button"
                        >
                          Đã phục vụ
                        </button>
                      ) : null}
                      {getLane(order) === "PaymentPending" ? (
                        <button
                          className="button primary"
                          disabled={busyOrderCode === order.orderCode}
                          onClick={() => confirmPayment(order)}
                          type="button"
                        >
                          Xác nhận thanh toán
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </article>
          );
        })}
      </section>
    </div>
  );
}

function getLane(order: OrderTrackingOrder): StaffLane {
  if (order.status === "Completed" || order.status === "Delivered") {
    return "Completed";
  }

  if (order.status === "Served") {
    return order.paymentStatus === "Paid" || order.paymentStatus === "Confirmed"
      ? "Completed"
      : "PaymentPending";
  }

  if (order.items.some((item) => item.status === "Ready")) {
    return "Ready";
  }

  return "PaymentPending";
}

function replaceOrder(orders: OrderTrackingOrder[], updatedOrder: OrderTrackingOrder) {
  return orders.map((order) => (order.orderId === updatedOrder.orderId ? updatedOrder : order));
}

function formatPayment(order: OrderTrackingOrder) {
  if (order.paymentStatus === "Paid" || order.paymentStatus === "Confirmed") {
    return "Đã thanh toán";
  }

  return `${order.paymentMethod ?? "COD"} - chờ xác nhận`;
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
