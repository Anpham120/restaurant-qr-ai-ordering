import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Timeline, type TimelineItem } from "@cmc/shared-ui";
import { VietQrPaymentModal } from "../../../components/customer/VietQrPaymentModal";
import "../../../components/order-tracking/realtime-order.css";
import {
  connectOrderRealtime,
  disconnectOrderRealtime,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
  watchOrderRealtime,
  type RealtimeConnectionStatus,
} from "../../../services/realtimeOrderService";
import { getOrderTracking } from "../../../services/orderService";
import type {
  OrderItemStatus,
  OrderRealtimeEvent,
  OrderStatusEvent,
  OrderTrackingItem,
  OrderTrackingOrder,
} from "../../../types";
import { PageShell } from "../../PageShell";

export function OrderTrackingPage() {
  const { orderCode = "ORD-1001" } = useParams();
  const [order, setOrder] = useState<OrderTrackingOrder | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<RealtimeConnectionStatus>("connected");
  const [errorMessage, setErrorMessage] = useState("");
  const [showVietQr, setShowVietQr] = useState(false);

  const handlePaymentConfirmed = useCallback(() => {
    getOrderTracking(orderCode).then(setOrder).catch(() => {});
  }, [orderCode]);

  useEffect(() => {
    getOrderTracking(orderCode)
      .then(setOrder)
      .catch(() => setErrorMessage("Không tải được trạng thái đơn hàng."));
  }, [orderCode]);

  useEffect(() => {
    const unsubscribeConnection = subscribeRealtimeConnection(setConnectionStatus);
    const unsubscribeRealtime = subscribeOrderRealtime((event) => {
      if (event.payload.orderCode !== orderCode) {
        return;
      }

      setOrder((current) => (current ? applyRealtimeEvent(current, event) : current));
    });

    void connectOrderRealtime()
      .then(() => watchOrderRealtime(orderCode, order?.tableCode))
      .catch(() => setConnectionStatus("error"));

    return () => {
      unsubscribeConnection();
      unsubscribeRealtime();
      void disconnectOrderRealtime();
    };
  }, [orderCode, order?.tableCode]);

  const stats = useMemo(() => {
    const items = order?.items ?? [];

    return [
      {
        label: "Trạng thái đơn",
        value: order?.status ?? "Loading",
        detail: "Cập nhật theo trạng thái hiện tại",
      },
      {
        label: "Món đang bếp",
        value: String(items.filter((item) => item.status === "Preparing").length),
        detail: "Theo dõi trạng thái chế biến",
      },
      {
        label: "Món Ready",
        value: String(items.filter((item) => item.status === "Ready").length),
        detail: "Không cần reload trang",
      },
    ];
  }, [order]);

  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title={`Đơn ${orderCode}`}
      description="Khách theo dõi trạng thái từng món theo thời gian thực, không cần tải lại trang."
      stats={stats}
    >
      <section className="realtime-status-bar">
        <div>
          <strong>Theo dõi món theo thời gian thực</strong>
          <p>Đang cập nhật trạng thái cho {orderCode}.</p>
        </div>
        <span className={`connection-pill connection-${connectionStatus}`}>
          {connectionStatus}
        </span>
      </section>

      {errorMessage ? <p className="realtime-error">{errorMessage}</p> : null}
      {order ? (
        <>
          <CustomerOrderTrackingPanel order={order} onShowVietQr={() => setShowVietQr(true)} />
          {showVietQr ? (
            <VietQrPaymentModal
              orderCode={order.orderCode}
              onClose={() => setShowVietQr(false)}
              onPaymentConfirmed={handlePaymentConfirmed}
            />
          ) : null}
        </>
      ) : <p>Đang tải đơn hàng...</p>}
    </PageShell>
  );
}

const itemStatusDescriptions: Record<OrderItemStatus, string> = {
  Pending: "Bếp đã nhận món và đang xếp hàng xử lý.",
  Preparing: "Đầu bếp đang chế biến món này.",
  Ready: "Món đã sẵn sàng để phục vụ.",
  Served: "Món đã được phục vụ.",
  Cancelled: "Món đã hủy.",
};

const timelineLabels: Record<string, string> = {
  Placed: "Đã ghi nhận",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Đã phục vụ",
};

// Vietnamese labels for the real status-history events (covers both order
// statuses and payment statuses, distinguished by event.source).
const eventStatusLabels: Record<string, string> = {
  Draft: "Nháp",
  Placed: "Đã đặt",
  Confirmed: "Đã xác nhận",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Đã phục vụ",
  Completed: "Hoàn tất",
  Cancelled: "Đã hủy",
  Unpaid: "Chưa thanh toán",
  Pending: "Chờ thanh toán",
  Paid: "Đã thanh toán",
  Failed: "Thanh toán lỗi",
  Refunded: "Đã hoàn tiền",
};

const eventTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

function formatEventTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : eventTimeFormatter.format(date);
}

function eventTone(event: OrderStatusEvent): TimelineItem["tone"] {
  switch (event.status) {
    case "Cancelled":
    case "Failed":
      return "danger";
    case "Refunded":
      return "warning";
    case "Completed":
    case "Served":
    case "Ready":
    case "Paid":
    case "Confirmed":
      return "success";
    default:
      return event.source === "Payment" ? "info" : "neutral";
  }
}

function toTimelineItems(events: OrderStatusEvent[]): TimelineItem[] {
  return events.map((event) => ({
    label: eventStatusLabels[event.status] ?? event.status,
    sublabel: event.source === "Payment" ? "Thanh toán" : "Trạng thái đơn",
    timestamp: formatEventTime(event.createdAt),
    tone: eventTone(event),
    note: event.note ?? undefined,
  }));
}

function CustomerOrderTrackingPanel({ order, onShowVietQr }: { order: OrderTrackingOrder; onShowVietQr: () => void }) {
  const readyCount = order.items.filter((item) => item.status === "Ready").length;
  const canPayVietQr =
    order.paymentMethod === "VietQR" &&
    (order.paymentStatus === "Unpaid" || order.paymentStatus === "Pending");

  return (
    <section className="order-tracking-panel" aria-label="Customer order tracking">
      <div className="tracking-summary-card">
        <div>
          <p className="tracking-kicker">Order tracking</p>
          <h3>{order.orderCode}</h3>
          <span>
            {order.tableCode ? `Bàn ${order.tableCode}` : "Mang về"} - {order.status}
          </span>
        </div>
        <strong>
          {readyCount}/{order.items.length}
          <small> món sẵn sàng</small>
        </strong>
      </div>

      {order.paymentStatus === "Refunded" ? (
        <p className="tracking-refunded" role="status">
          Đơn này đã được hoàn tiền. Vui lòng liên hệ nhân viên nếu cần hỗ trợ thêm.
        </p>
      ) : null}

      {order.pickupInfo ? (
        <div className="tracking-pickup">
          <p className="tracking-kicker">Thông tin nhận món</p>
          <strong>{order.pickupInfo.customerName}</strong>
          <span>{order.pickupInfo.phoneNumber}</span>
        </div>
      ) : null}

      <div className="tracking-timeline">
        {["Placed", "Preparing", "Ready", "Served"].map((status, index) => (
          <div className={getTimelineClass(order.status, status)} key={status}>
            <span>{index + 1}</span>
            <div>
              <h3>{timelineLabels[status]}</h3>
              <p>{getTimelineCopy(status)}</p>
            </div>
          </div>
        ))}
      </div>

      {order.events && order.events.length > 0 ? (
        <div className="tracking-history">
          <p className="tracking-kicker">Lịch sử xử lý</p>
          <Timeline items={toTimelineItems(order.events)} />
        </div>
      ) : null}

      <div className="tracking-item-list">
        {order.items.map((item) => (
          <article className="tracking-item" key={item.orderItemId}>
            <div>
              <strong>{item.name}</strong>
              <p>
                x{item.quantity} - {itemStatusDescriptions[item.status]}
              </p>
            </div>
            <span className={`status-pill status-${item.status.toLowerCase()}`}>
              {item.status}
            </span>
          </article>
        ))}
      </div>

      {canPayVietQr ? (
        <div className="tracking-vietqr-action">
          <button className="button primary" type="button" onClick={onShowVietQr}>
            💳 Thanh toán VietQR
          </button>
          <p>Quét mã QR để chuyển khoản nhanh</p>
        </div>
      ) : null}
    </section>
  );
}

function applyRealtimeEvent(
  order: OrderTrackingOrder,
  event: OrderRealtimeEvent,
): OrderTrackingOrder {
  if (event.event === "order.statusChanged") {
    return {
      ...order,
      status: event.payload.status,
      updatedAt: event.payload.updatedAt,
    };
  }

  if (event.event !== "order.itemStatusChanged") {
    return order;
  }

  const items = order.items.map((item) =>
    item.orderItemId === event.payload.orderItemId
      ? {
          ...item,
          status: event.payload.status,
          updatedAt: event.payload.updatedAt,
        }
      : item,
  );

  return {
    ...order,
    status: calculateOrderStatus(items),
    updatedAt: event.payload.updatedAt,
    items,
  };
}

function calculateOrderStatus(items: OrderTrackingItem[]) {
  if (items.every((item) => item.status === "Ready" || item.status === "Served")) {
    return "Ready" as const;
  }

  if (items.some((item) => item.status === "Preparing" || item.status === "Ready")) {
    return "Preparing" as const;
  }

  return "Placed" as const;
}

function getTimelineCopy(status: string) {
  switch (status) {
    case "Placed":
      return "Đơn đã được ghi nhận.";
    case "Preparing":
      return "Bếp đang xử lý các món.";
    case "Ready":
      return "Món sẵn sàng để mang ra.";
    default:
      return "Nhân viên xác nhận phục vụ.";
  }
}

function getTimelineClass(currentStatus: string, timelineStatus: string) {
  const order = ["Placed", "Preparing", "Ready", "Served"];
  const currentIndex = order.indexOf(currentStatus);
  const timelineIndex = order.indexOf(timelineStatus);

  return timelineIndex <= currentIndex
    ? "tracking-step tracking-step-active"
    : "tracking-step";
}
