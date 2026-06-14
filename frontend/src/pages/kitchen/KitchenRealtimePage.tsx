import { useEffect, useMemo, useState } from "react";
import { AdminStatePanel } from "../../components/admin/AdminStatePanel";
import { KitchenBoard } from "../../components/kitchen/KitchenBoard";
import "../../components/order-tracking/realtime-order.css";
import {
  connectOrderRealtime,
  disconnectOrderRealtime,
  createItemStatusChangedEvent,
  publishOrderRealtimeEvent,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
  type RealtimeConnectionStatus,
} from "../../services/realtimeOrderService";
import { getKitchenOrders, updateOrderItemStatus } from "../../services/orderService";
import type {
  OrderItemStatus,
  OrderRealtimeEvent,
  OrderTrackingItem,
  OrderTrackingOrder,
} from "../../types";
import { PageShell } from "../PageShell";

export function KitchenRealtimePage() {
  const [orders, setOrders] = useState<OrderTrackingOrder[]>([]);
  const [connectionStatus, setConnectionStatus] =
    useState<RealtimeConnectionStatus>("connected");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    getKitchenOrders()
      .then(setOrders)
      .catch(() => setErrorMessage("Không tải được danh sách đơn bếp."))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    const unsubscribeConnection = subscribeRealtimeConnection(setConnectionStatus);
    const unsubscribeRealtime = subscribeOrderRealtime((event) => {
      setOrders((current) => applyRealtimeEvent(current, event));
    });
    void connectOrderRealtime().catch(() => setConnectionStatus("error"));

    return () => {
      unsubscribeConnection();
      unsubscribeRealtime();
      void disconnectOrderRealtime();
    };
  }, []);

  const stats = useMemo(() => {
    const items = orders.flatMap((order) => order.items);

    return [
      {
        label: "Pending",
        value: String(items.filter((item) => item.status === "Pending").length),
        detail: "Món mới vào hàng đợi",
      },
      {
        label: "Preparing",
        value: String(items.filter((item) => item.status === "Preparing").length),
        detail: "Bếp đang chế biến",
      },
      {
        label: "Ready",
        value: String(items.filter((item) => item.status === "Ready").length),
        detail: "Chờ staff mang ra",
      },
    ];
  }, [orders]);

  async function handleUpdateItemStatus(
    order: OrderTrackingOrder,
    item: OrderTrackingItem,
    status: OrderItemStatus,
  ) {
    setErrorMessage("");

    try {
      const updatedOrder = await updateOrderItemStatus(
        order.orderCode,
        item.orderItemId,
        status,
      );

      publishOrderRealtimeEvent(
        createItemStatusChangedEvent(updatedOrder, item.orderItemId, status),
      );
    } catch {
      setErrorMessage("Không cập nhật được trạng thái món.");
    }
  }

  return (
    <PageShell
      eyebrow="Kitchen realtime"
      title="Bảng bếp CMC"
      description="Bếp nhận món theo cột Pending, Preparing, Ready và cập nhật trạng thái để khách cùng nhân viên theo dõi."
      variant="kitchen"
      stats={stats}
    >
      <RealtimeStatusBar
        connectionStatus={connectionStatus}
      />

      {errorMessage ? <p className="realtime-error">{errorMessage}</p> : null}

      {isLoading ? (
        <AdminStatePanel
          title="Đang tải bảng bếp"
          description="Đang lấy danh sách đơn hiện có cho bếp."
        />
      ) : (
        <KitchenBoard orders={orders} onUpdateItemStatus={handleUpdateItemStatus} />
      )}

    </PageShell>
  );
}

function RealtimeStatusBar({
  connectionStatus,
}: {
  connectionStatus: RealtimeConnectionStatus;
}) {
  const statusLabel =
    connectionStatus === "connected"
      ? "Đã kết nối"
      : connectionStatus === "reconnecting"
        ? "Đang kết nối lại"
        : "Mất kết nối";

  return (
    <section className="realtime-status-bar">
      <div>
        <strong>Kết nối cập nhật trạng thái</strong>
        <p>Bếp cập nhật món để khách và nhân viên theo dõi cùng một luồng.</p>
      </div>
      <span className={`connection-pill connection-${connectionStatus}`}>
        {statusLabel}
      </span>
    </section>
  );
}

function applyRealtimeEvent(
  orders: OrderTrackingOrder[],
  event: OrderRealtimeEvent,
): OrderTrackingOrder[] {
  if (event.event === "order.itemStatusChanged") {
    return orders.map((order) => {
      if (order.orderCode !== event.payload.orderCode) {
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
    });
  }

  if (event.event === "order.statusChanged") {
    return orders.map((order) =>
      order.orderCode === event.payload.orderCode
        ? { ...order, status: event.payload.status, updatedAt: event.payload.updatedAt }
        : order,
    );
  }

  return orders;
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
