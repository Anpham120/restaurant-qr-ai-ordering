import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Timeline, type TimelineItem } from "@cmc/shared-ui";
import { VietQrPaymentModal } from "../../../components/customer/VietQrPaymentModal";
import "../../../components/customer/customer-order-tracking.css";
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

/* ========================================================================
   Labels & Helpers
   ======================================================================== */

const itemStatusLabels: Record<OrderItemStatus, string> = {
  Pending: "Chờ xử lý",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Đã phục vụ",
  Cancelled: "Đã hủy",
};

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
    ? "cmc-ot-step cmc-ot-step-active"
    : "cmc-ot-step";
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

/* ========================================================================
   Main Page
   ======================================================================== */

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

    return {
      statusLabel: eventStatusLabels[order?.status ?? ""] ?? "Đang tải",
      preparing: items.filter((item) => item.status === "Preparing").length,
      ready: items.filter((item) => item.status === "Ready").length,
    };
  }, [order]);

  const connectionLabel =
    connectionStatus === "connected"
      ? "Đã kết nối"
      : connectionStatus === "reconnecting"
        ? "Đang kết nối lại…"
        : "Lỗi kết nối";

  return (
    <section className="cmc-order-tracking">
      {/* Hero */}
      <header className="cmc-ot-hero">
        <p className="cmc-ot-kicker">CMC Restaurant</p>
        <h2>
          Theo dõi đơn <span>{orderCode}</span>
        </h2>
        <p>
          Trạng thái từng món được cập nhật theo thời gian thực — không cần tải
          lại trang.
        </p>

        <div className="cmc-ot-hero-stats">
          <article className="cmc-ot-stat">
            <strong>{stats.statusLabel}</strong>
            <span>Trạng thái đơn</span>
          </article>
          <article className="cmc-ot-stat">
            <strong>{stats.preparing}</strong>
            <span>Đang chế biến</span>
          </article>
          <article className="cmc-ot-stat">
            <strong>{stats.ready}</strong>
            <span>Sẵn sàng</span>
          </article>
        </div>
      </header>

      {/* Connection bar */}
      <div className="cmc-ot-connection-bar">
        <div>
          <strong>Theo dõi món theo thời gian thực</strong>
          <p>Đang cập nhật trạng thái cho {orderCode}.</p>
        </div>
        <span className={`cmc-ot-pill cmc-ot-pill-${connectionStatus}`}>
          {connectionLabel}
        </span>
      </div>

      {errorMessage ? (
        <p className="cmc-ot-error">{errorMessage}</p>
      ) : null}

      {order ? (
        <div className="cmc-ot-content">
          <OrderTrackingPanel
            order={order}
            onShowVietQr={() => setShowVietQr(true)}
          />

          {showVietQr ? (
            <VietQrPaymentModal
              orderCode={order.orderCode}
              onClose={() => setShowVietQr(false)}
              onPaymentConfirmed={handlePaymentConfirmed}
            />
          ) : null}

          {/* Back link */}
          <Link className="cmc-ot-back" to="/">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              width="16"
              height="16"
            >
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Về trang chủ
          </Link>
        </div>
      ) : (
        <p className="cmc-ot-loading">Đang tải đơn hàng…</p>
      )}
    </section>
  );
}

/* ========================================================================
   Tracking Panel (within content area)
   ======================================================================== */

function OrderTrackingPanel({
  order,
  onShowVietQr,
}: {
  order: OrderTrackingOrder;
  onShowVietQr: () => void;
}) {
  const readyCount = order.items.filter((item) => item.status === "Ready").length;
  const canPayVietQr =
    order.paymentMethod === "VietQR" &&
    (order.paymentStatus === "Unpaid" || order.paymentStatus === "Pending");

  return (
    <>
      {/* Summary card */}
      <div className="cmc-ot-summary">
        <div>
          <p className="cmc-ot-kicker">Theo dõi đơn</p>
          <h3>{order.orderCode}</h3>
          <span>
            {order.tableCode ? `Bàn ${order.tableCode}` : "Chưa có bàn"} —{" "}
            {eventStatusLabels[order.status] ?? order.status}
          </span>
        </div>
        <strong>
          {readyCount}/{order.items.length}
          <small>món sẵn sàng</small>
        </strong>
      </div>

      {/* Refund notice */}
      {order.paymentStatus === "Refunded" ? (
        <p className="cmc-ot-refunded" role="status">
          Đơn này đã được hoàn tiền. Vui lòng liên hệ nhân viên nếu cần hỗ trợ
          thêm.
        </p>
      ) : null}

      {/* Progress timeline */}
      <div className="cmc-ot-timeline">
        {(["Placed", "Preparing", "Ready", "Served"] as const).map(
          (status, index) => (
            <div className={getTimelineClass(order.status, status)} key={status}>
              <span>{index + 1}</span>
              <div>
                <h3>{timelineLabels[status]}</h3>
                <p>{getTimelineCopy(status)}</p>
              </div>
            </div>
          ),
        )}
      </div>

      {/* Event history */}
      {order.events && order.events.length > 0 ? (
        <div className="cmc-ot-history">
          <p className="cmc-ot-kicker">Lịch sử xử lý</p>
          <Timeline items={toTimelineItems(order.events)} />
        </div>
      ) : null}

      {/* Item list */}
      <div className="cmc-ot-item-list">
        <p className="cmc-ot-kicker">Chi tiết món</p>
        {order.items.map((item) => (
          <article className="cmc-ot-item" key={item.orderItemId}>
            <div>
              <strong>{item.name}</strong>
              <p>
                x{item.quantity} — {itemStatusDescriptions[item.status]}
              </p>
            </div>
            <span
              className={`cmc-ot-item-pill cmc-ot-item-${item.status.toLowerCase()}`}
            >
              {itemStatusLabels[item.status] ?? item.status}
            </span>
          </article>
        ))}
      </div>

      {/* VietQR action */}
      {canPayVietQr ? (
        <div className="cmc-ot-vietqr-action">
          <button type="button" onClick={onShowVietQr}>
            💳 Thanh toán VietQR
          </button>
          <p>Quét mã QR để chuyển khoản nhanh</p>
        </div>
      ) : null}
    </>
  );
}
