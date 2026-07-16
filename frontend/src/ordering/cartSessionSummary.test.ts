import { describe, expect, it } from "vitest";
import { buildCartSessionSummary } from "./cartSessionSummary";

describe("cart session summary", () => {
  it("keeps previous order rounds in the projected table total", () => {
    const summary = buildCartSessionSummary(
      {
        subtotalAmount: 175_000,
        orderRounds: [{ orderCode: "ORD-1" }, { orderCode: "ORD-2" }],
      },
      [
        { quantity: 2, unitPrice: 75_000 },
        { quantity: 1, unitPrice: 85_000 },
      ],
    );

    expect(summary).toEqual({
      orderedSubtotal: 175_000,
      cartSubtotal: 235_000,
      projectedTotal: 410_000,
      orderRoundCount: 2,
      selectedQuantity: 3,
    });
  });

  it("uses only the current cart before the first order round", () => {
    expect(
      buildCartSessionSummary(null, [{ quantity: 1, unitPrice: 55_000 }]),
    ).toEqual({
      orderedSubtotal: 0,
      cartSubtotal: 55_000,
      projectedTotal: 55_000,
      orderRoundCount: 0,
      selectedQuantity: 1,
    });
  });
});
