import { describe, expect, it } from "vitest";
import { getKitchenBoardColumn, isKitchenActiveOrderStatus } from "./kitchenOrderPipeline";

describe("kitchen order pipeline", () => {
  it("shows newly placed orders in the new-order column", () => {
    expect(getKitchenBoardColumn("Placed")).toBe("confirmed");
    expect(getKitchenBoardColumn("Confirmed")).toBe("confirmed");
    expect(isKitchenActiveOrderStatus("Placed")).toBe(true);
  });

  it("keeps only active kitchen statuses on the board", () => {
    expect(getKitchenBoardColumn("Preparing")).toBe("preparing");
    expect(getKitchenBoardColumn("Ready")).toBe("ready");
    expect(getKitchenBoardColumn("Served")).toBe("served");
    expect(isKitchenActiveOrderStatus("Served")).toBe(true);
    expect(getKitchenBoardColumn("Completed")).toBeNull();
    expect(getKitchenBoardColumn("Cancelled")).toBeNull();
  });
});
