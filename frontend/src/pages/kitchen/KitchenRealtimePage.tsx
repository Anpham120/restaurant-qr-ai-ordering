import { useCallback, useEffect, useMemo, useState } from "react";
import type { Order, OrderStatus, RealtimeConnectionStatus } from "@cmc/shared-types";
import { KitchenBoard } from "../../components/kitchen/KitchenBoard";
import {
  connectOrderRealtime,
  disconnectOrderRealtime,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
} from "../../services/realtimeOrderService";
import { getKitchenOrders } from "../../services/orderService";
import { fetchAdminMenuItems, toggleMenuItemAvailability } from "../../services/adminMenuService";
import "../../components/operations/operations.css";

type MenuItemSummary = { id: string; name: string; isAvailable: boolean };

const KITCHEN_STATUSES: OrderStatus[] = ["Confirmed", "Preparing", "Ready"];

export function KitchenRealtimePage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItemSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [connectionStatus, setConnectionStatus] = useState<RealtimeConnectionStatus>("disconnected");
  const [showMenuPanel, setShowMenuPanel] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  // Filter orders relevant to kitchen
  const kitchenOrders = useMemo(
    () => orders.filter((o) => KITCHEN_STATUSES.includes(o.status)),
    [orders],
  );

  const stats = useMemo(() => {
    const confirmed = kitchenOrders.filter((o) => o.status === "Confirmed").length;
    const preparing = kitchenOrders.filter((o) => o.status === "Preparing").length;
    const ready = kitchenOrders.filter((o) => o.status === "Ready").length;
    const totalItems = kitchenOrders.reduce(
      (sum, o) => sum + o.items.filter((i) => i.status !== "Cancelled").length,
      0,
    );
    return [
      { label: "Đơn chờ nấu", value: String(confirmed), detail: "Confirmed" },
      { label: "Đang nấu", value: String(preparing), detail: "Preparing" },
      { label: "Sẵn sàng", value: String(ready), detail: "Chờ Staff mang ra" },
      { label: "Tổng món", value: String(totalItems), detail: "Trong pipeline" },
    ];
  }, [kitchenOrders]);

  const unavailableCount = useMemo(
    () => menuItems.filter((m) => !m.isAvailable).length,
    [menuItems],
  );

  // Load data
  const loadOrders = useCallback(async () => {
    try {
      const data = await getKitchenOrders();
      setOrders(data as unknown as Order[]);
    } catch {
      setError("Không tải được đơn hàng.");
    }
  }, []);

  const loadMenu = useCallback(async () => {
    try {
      const items = await fetchAdminMenuItems();
      setMenuItems(
        items.map((i: { id: string; name: string; isAvailable: boolean }) => ({
          id: i.id,
          name: i.name,
          isAvailable: i.isAvailable,
        })),
      );
    } catch {
      /* non-critical */
    }
  }, []);

  useEffect(() => {
    Promise.all([loadOrders(), loadMenu()]).finally(() => setIsLoading(false));
  }, [loadOrders, loadMenu]);

  // Realtime
  useEffect(() => {
    const unsubConnection = subscribeRealtimeConnection(setConnectionStatus);
    const unsubRealtime = subscribeOrderRealtime(() => {
      // Any order event → refresh entire list
      loadOrders();
    });

    void connectOrderRealtime().catch(() => setConnectionStatus("error"));

    return () => {
      unsubConnection();
      unsubRealtime();
      void disconnectOrderRealtime();
    };
  }, [loadOrders]);

  // Toggle dish availability
  async function handleToggleAvailability(itemId: string, currentlyAvailable: boolean) {
    setTogglingId(itemId);
    try {
      await toggleMenuItemAvailability(itemId, !currentlyAvailable);
      setMenuItems((prev) =>
        prev.map((m) => (m.id === itemId ? { ...m, isAvailable: !currentlyAvailable } : m)),
      );
    } catch {
      setError("Không thể cập nhật trạng thái món.");
    } finally {
      setTogglingId(null);
    }
  }

  if (isLoading) {
    return (
      <div className="ops-empty">
        <div className="ops-empty-icon">🍳</div>
        Đang tải bảng bếp...
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="ops-page-header">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1>Bảng Bếp</h1>
            <p>Theo dõi và cập nhật trạng thái đơn hàng realtime</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className={`ops-connection ops-connection--${connectionStatus}`}>
              <span className="ops-connection-dot" />
              {connectionStatus === "connected" ? "Đã kết nối" :
                connectionStatus === "connecting" ? "Đang kết nối..." :
                  connectionStatus === "reconnecting" ? "Đang kết nối lại..." : "Mất kết nối"}
            </span>
            <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={loadOrders} type="button">
              🔄 Làm mới
            </button>
            <button
              className="ops-btn ops-btn--ghost ops-btn--sm"
              onClick={() => { setShowMenuPanel(!showMenuPanel); if (!showMenuPanel) loadMenu(); }}
              type="button"
            >
              🍽 Tắt/Mở món {unavailableCount > 0 ? `(${unavailableCount} hết)` : ""}
            </button>
          </div>
        </div>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}

      {/* Stats */}
      <div className="ops-stats">
        {stats.map((s) => (
          <div className="ops-stat-card" key={s.label}>
            <div className="ops-stat-label">{s.label}</div>
            <div className="ops-stat-value">{s.value}</div>
            <div className="ops-stat-detail">{s.detail}</div>
          </div>
        ))}
      </div>

      {/* Toggle menu panel */}
      {showMenuPanel ? (
        <div style={{ marginBottom: 20, padding: 16, background: "var(--color-bg-subtle)", borderRadius: 12, maxHeight: 300, overflowY: "auto" }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 15 }}>Quản lý tình trạng món</h3>
          {menuItems.map((item) => (
            <div className="ops-toggle-row" key={item.id}>
              <span className="ops-toggle-label">
                {item.name}
                {!item.isAvailable ? <span className="ops-badge ops-badge--cancelled" style={{ marginLeft: 8 }}>Hết</span> : null}
              </span>
              <button
                className={`ops-toggle-switch ${item.isAvailable ? "ops-toggle-switch--on" : ""}`}
                disabled={togglingId === item.id}
                onClick={() => handleToggleAvailability(item.id, item.isAvailable)}
                type="button"
                aria-label={`${item.isAvailable ? "Tắt" : "Mở"} ${item.name}`}
              />
            </div>
          ))}
        </div>
      ) : null}

      {/* Board */}
      <KitchenBoard orders={kitchenOrders} onRefresh={loadOrders} />
    </div>
  );
}
