import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@cmc/i18n";
import type { TableInvoice } from "../types";
import { TableInvoicePaymentModal } from "./TableInvoicePaymentModal";
import { getInvoicePaymentTotal, validateAppliedPromotion } from "./tableInvoicePaymentModel";

const invoice: TableInvoice = {
  tableSessionId: "session-1",
  invoiceCode: null,
  tableCode: "T04",
  status: "NotRequested",
  subtotalAmount: 220_000,
  discountAmount: 0,
  totalAmount: 220_000,
  promotionCode: null,
  customerPhoneNumber: null,
  method: "Unselected",
  orderRounds: [
    { orderCode: "ORD-1", status: "Placed", subtotalAmount: 55_000, createdAt: "2026-07-12T10:00:00Z" },
    { orderCode: "ORD-2", status: "Placed", subtotalAmount: 165_000, createdAt: "2026-07-12T10:10:00Z" },
  ],
  items: [
    { menuItemId: "item-1", name: "Phở bò", unitPrice: 55_000, quantity: 4, lineTotal: 220_000 },
  ],
  vietQr: null,
};

describe("table invoice payment lifecycle", () => {
  it("renders one settlement form for all order rounds", () => {
    const html = renderToStaticMarkup(
      createElement(
        I18nProvider,
        null,
        createElement(TableInvoicePaymentModal, {
          invoice,
          onClose: vi.fn(),
          onRequest: vi.fn(),
        }),
      ),
    );

    expect(html).toContain("2 lần gọi món");
    expect(html).toMatch(/220\.000(?:\u00a0|\s)₫/);
    expect(html).toContain("Mã ưu đãi");
    expect(html).toContain("Số điện thoại tích điểm");
    expect(html).toContain("Phương thức thanh toán");
  });

  it("shows the final promoted total only after a validated preview", () => {
    const preview = { code: "GIAM10", discountAmount: 22_000, totalAmount: 198_000 };

    expect(getInvoicePaymentTotal(invoice, null)).toBe(220_000);
    expect(getInvoicePaymentTotal(invoice, preview)).toBe(198_000);
    expect(validateAppliedPromotion("giam10", null)).toContain("bấm Áp dụng");
    expect(validateAppliedPromotion("giam10", preview)).toBeNull();
  });
});
