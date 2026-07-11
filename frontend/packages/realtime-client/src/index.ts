import { HubConnectionBuilder, HubConnectionState, LogLevel, type HubConnection } from "@microsoft/signalr";
import type { OrderCreatedEvent, OrderItemStatusChangedEvent, OrderStatusChangedEvent, PaymentRequestedEvent, RealtimeConnectionStatus } from "@cmc/shared-types";
export type OrderRealtimeHandlers = { onOrderCreated?: (event: OrderCreatedEvent) => void; onOrderStatusChanged?: (event: OrderStatusChangedEvent) => void; onOrderItemStatusChanged?: (event: OrderItemStatusChangedEvent) => void; onPaymentRequested?: (event: PaymentRequestedEvent) => void; onStatusChanged?: (status: RealtimeConnectionStatus) => void };
export function createOrderHubClient(options: { hubUrl?: string; accessTokenFactory?: () => string | null; handlers?: OrderRealtimeHandlers } = {}) {
  const handlers = options.handlers ?? {};
  const hubUrl = options.hubUrl ?? import.meta.env.VITE_ORDER_HUB_URL ?? "https://localhost:7296/hubs/orders";
  let connection: HubConnection | null = null;
  let operation = Promise.resolve();

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
    connection.onreconnecting(() => handlers.onStatusChanged?.("reconnecting"));
    connection.onreconnected(() => handlers.onStatusChanged?.("connected"));
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
      });
    },
    async watchOrder(orderCode: string, orderToken: string) { await (connection ?? build()).invoke("WatchOrder", orderCode, orderToken); },
    async watchTable(tableCode: string) { await (connection ?? build()).invoke("WatchTable", tableCode); },
  };
}
