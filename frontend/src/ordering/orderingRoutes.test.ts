import { describe, expect, it } from "vitest";
import { orderTrackingPath, orderingPath } from "./orderingRoutes";

describe("ordering routes", () => {
  it("keeps every transactional destination under its table-session boundary", () => {
    expect(orderingPath("session-123", "ai")).toBe("/table-session/session-123/ai");
    expect(orderingPath("session-123", "cart")).toBe("/table-session/session-123/cart");
    expect(orderingPath("session-123", "orders")).toBe("/table-session/session-123/orders");
  });

  it("preserves the session boundary when opening an individual order", () => {
    expect(orderTrackingPath("session/123", "ORD #1")).toBe("/table-session/session%2F123/orders/ORD%20%231");
  });
});
