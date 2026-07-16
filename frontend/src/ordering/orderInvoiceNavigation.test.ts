import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("order invoice navigation", () => {
  it("returns to the table-session invoice instead of the menu redirect", () => {
    const pagePath = fileURLToPath(
      new URL("../pages/customer/orders/OrderTrackingPage.tsx", import.meta.url),
    );
    const page = readFileSync(pagePath, "utf8");

    expect(page).toContain('invoicePath={orderingPath(sessionId, "orders")}');
    expect(page).toContain("to={invoicePath}");
    expect(page).not.toContain('to=".."');
  });
});
