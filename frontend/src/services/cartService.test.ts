import { describe, expect, it } from "vitest";
import { CartApiError, formatCartErrorMessage } from "./cartService";

describe("formatCartErrorMessage", () => {
  it("maps known cart conflict codes to customer-facing copy", () => {
    expect(
      formatCartErrorMessage(
        new CartApiError(409, "TABLE_INVOICE_PAYMENT_PENDING", "pending"),
      ),
    ).toContain("thanh toán");
  });

  it("falls back to the API message for unknown codes", () => {
    expect(
      formatCartErrorMessage(new CartApiError(400, "UNKNOWN", "Server said no")),
    ).toBe("Server said no");
  });
});
