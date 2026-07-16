import { describe, expect, it } from "vitest";
import {
  canDropKitchenOrder,
  getKitchenBoardAdvancePlan,
  getKitchenBoardColumn,
  getNextKitchenBoardColumn,
  isKitchenActiveOrderStatus,
} from "./kitchenOrderPipeline";

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

  it("advances each card exactly one lane at a time", () => {
    expect(getKitchenBoardAdvancePlan("Placed")).toEqual({
      kind: "items",
      eligibleItemStatuses: ["Pending"],
      nextItemStatus: "Preparing",
    });
    expect(getKitchenBoardAdvancePlan("Preparing")).toEqual({
      kind: "items",
      eligibleItemStatuses: ["Pending", "Preparing"],
      nextItemStatus: "Ready",
    });
    expect(getKitchenBoardAdvancePlan("Ready")).toEqual({
      kind: "order",
      nextOrderStatus: "Served",
    });
    expect(getKitchenBoardAdvancePlan("Served")).toBeNull();
  });

  it("accepts drag/drop only into the immediate next lane", () => {
    expect(getNextKitchenBoardColumn("Placed")).toBe("preparing");
    expect(getNextKitchenBoardColumn("Preparing")).toBe("ready");
    expect(getNextKitchenBoardColumn("Ready")).toBe("served");
    expect(getNextKitchenBoardColumn("Served")).toBeNull();

    expect(canDropKitchenOrder("Placed", "preparing")).toBe(true);
    expect(canDropKitchenOrder("Preparing", "ready")).toBe(true);
    expect(canDropKitchenOrder("Ready", "served")).toBe(true);
    expect(canDropKitchenOrder("Placed", "ready")).toBe(false);
    expect(canDropKitchenOrder("Preparing", "confirmed")).toBe(false);
    expect(canDropKitchenOrder("Served", "ready")).toBe(false);
  });
});
