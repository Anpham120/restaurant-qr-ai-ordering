import { HubConnectionBuilder, HubConnectionState, LogLevel, type HubConnection } from "@microsoft/signalr";
import type { OrderCreatedEvent, OrderItemStatusChangedEvent, OrderStatusChangedEvent, PaymentRequestedEvent, RealtimeConnectionStatus } from "@cmc/shared-types";

export type CartUpdatedEvent = {
  tableSessionId: string;
  tableCode: string | null;
  itemCount: number;
  subtotal: number;
  updatedAt: string;
};

export type AssistanceRequestedEvent = {
  tableCode: string;
  tableSessionId: string | null;
  note: string | null;
  requestedAt: string;
};

/** Backend event name: menu.availabilityChanged */
export type MenuAvailabilityChangedEvent = {
  menuItemId: string;
  isAvailable: boolean;
  updatedAt: string;
};

export type OrderRealtimeHandlers = {
  onOrderCreated?: (event: OrderCreatedEvent) => void;
  onOrderStatusChanged?: (event: OrderStatusChangedEvent) => void;
  onOrderItemStatusChanged?: (event: OrderItemStatusChangedEvent) => void;
  onPaymentRequested?: (event: PaymentRequestedEvent) => void;
  onCartUpdated?: (event: CartUpdatedEvent) => void;
  onAssistanceRequested?: (event: AssistanceRequestedEvent) => void;
  onMenuAvailabilityChanged?: (event: MenuAvailabilityChangedEvent) => void;
  onStatusChanged?: (status: RealtimeConnectionStatus) => void;
};

export function createOrderHubClient(options: { hubUrl?: string; accessTokenFactory?: () => string | null; handlers?: OrderRealtimeHandlers } = {}) {
  const handlers = options.handlers ?? {};
  const hubUrl = options.hubUrl ?? import.meta.env.VITE_ORDER_HUB_URL ?? "https://localhost:7296/hubs/orders";
  let connection: HubConnection | null = null;
  let operation = Promise.resolve();
  const activeWatches = new Map<string, { method: string; args: unknown[] }>();

  async function restoreWatches() {
    if (!connection) return;
    for (const watch of activeWatches.values()) {
      await connection.invoke(watch.method, ...watch.args);
    }
  }

  async function watch(key: string, method: string, ...args: unknown[]) {
    const current = connection ?? build();
    await current.invoke(method, ...args);
    activeWatches.set(key, { method, args });
  }

  function build() {
    const builder = new HubConnectionBuilder().withUrl(hubUrl, {
      accessTokenFactory: () => options.accessTokenFactory?.() ?? "",
      withCredentials: false,
    }).withAutomaticReconnect().configureLogging(LogLevel.Warning);
    connection = builder.build();
    connection.on("order.created", event => handlers.onOrderCreated?.(event));
    connection.on("order.statusChanged", event => handlers.onOrderStatusChanged?.(event));
    connection.on("order.itemStatusChanged", event => handlers.onOrderItemStatusChanged?.(event));
    connection.on("payment.requested", event => handlers.onPaymentRequested?.(event));
    connection.on("cart.updated", event => handlers.onCartUpdated?.(event));
    connection.on("assistance.requested", event => handlers.onAssistanceRequested?.(event));
    connection.on("menu.availabilityChanged", event => handlers.onMenuAvailabilityChanged?.(event));
    connection.onreconnecting(() => handlers.onStatusChanged?.("reconnecting"));
    connection.onreconnected(async () => {
      try {
        await restoreWatches();
        handlers.onStatusChanged?.("connected");
      } catch {
        handlers.onStatusChanged?.("error");
      }
    });
    connection.onclose(error => handlers.onStatusChanged?.(error ? "error" : "disconnected"));
    return connection;
  }

  function enqueue(task: () => Promise<void>) {
    const nextOperation = operation.then(task, task);
    operation = nextOperation.catch(() => undefined);
    return nextOperation;
  }

  return {
    connect() {
      return enqueue(async () => {
        const current = connection ?? build();
        if (current.state === HubConnectionState.Disconnected) {
          handlers.onStatusChanged?.("connecting");
          await current.start();
          handlers.onStatusChanged?.("connected");
        }
      });
    },
    disconnect() {
      return enqueue(async () => {
        if (connection && connection.state !== HubConnectionState.Disconnected) {
          await connection.stop();
        }
        activeWatches.clear();
      });
    },
    async watchOrder(orderCode: string, orderToken: string) { await watch("order", "WatchOrder", orderCode, orderToken); },
    async watchTable(tableCode: string) { await watch("table", "WatchTable", tableCode); },
    async watchTableSession(tableSessionId: string, sessionToken: string) { await watch("table-session", "WatchTableSession", tableSessionId, sessionToken); },
  };
}
