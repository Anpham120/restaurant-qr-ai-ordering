import { useEffect, useRef } from "react";
import { useI18n } from "@cmc/i18n";
import { localizeMenuItemName } from "@cmc/i18n/menu";
import { CheckCircle2, ReceiptText, X } from "lucide-react";
import type { TableInvoice } from "../types";

type Props = {
  invoice: TableInvoice;
  paidAt: string;
  tableDisplayName?: string | null;
  onClose: () => void;
};

export function TableElectronicReceiptModal({ invoice, paidAt, tableDisplayName, onClose }: Props) {
  const { formatDateTime, formatMoney, locale, t } = useI18n();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const tableLabel = tableDisplayName ?? invoice.tableCode ?? "—";

  return (
    <div
      className="table-invoice-overlay table-e-receipt-overlay"
      onClick={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
    >
      <section
        aria-labelledby="e-receipt-title"
        aria-modal="true"
        className="table-invoice-modal table-e-receipt-modal"
        role="dialog"
      >
        <header className="table-invoice-modal-header table-e-receipt-header">
          <div>
            <span className="table-e-receipt-kicker">
              <CheckCircle2 aria-hidden="true" size={18} />
              {t("Thanh toán thành công!")}
            </span>
            <h2 id="e-receipt-title">{t("Hóa đơn điện tử")}</h2>
          </div>
          <button aria-label={t("Đóng")} onClick={onClose} ref={closeRef} type="button">
            <X aria-hidden="true" size={20} />
          </button>
        </header>

        <div className="table-e-receipt-body">
          <div className="table-e-receipt-brand">
            <strong>CMC Restaurant</strong>
            <span>{t("Bàn {table}", { table: tableLabel })}</span>
            <span>{formatDateTime(paidAt)}</span>
            {invoice.invoiceCode ? (
              <span>
                {t("Mã HĐ")}: <code>{invoice.invoiceCode}</code>
              </span>
            ) : null}
          </div>

          <section aria-label={t("Tóm tắt hóa đơn")} className="table-invoice-receipt table-e-receipt-lines">
            <div className="table-invoice-receipt-title">
              <ReceiptText aria-hidden="true" size={20} />
              <strong>{t("{count} lần gọi món", { count: invoice.orderRounds.length })}</strong>
            </div>
            <ul>
              {invoice.items.map((item) => (
                <li key={item.menuItemId}>
                  <span>
                    {item.quantity}× {localizeMenuItemName(item.menuItemId, item.name, locale)}
                  </span>
                  <strong data-money>{formatMoney(item.lineTotal)}</strong>
                </li>
              ))}
            </ul>
            <div className="table-invoice-total-row">
              <span>{t("Tạm tính")}</span>
              <strong data-money>{formatMoney(invoice.subtotalAmount)}</strong>
            </div>
            {invoice.discountAmount > 0 ? (
              <div className="table-invoice-discount-row">
                <span>{t("Ưu đãi {code}", { code: invoice.promotionCode ?? "" })}</span>
                <strong data-money>-{formatMoney(invoice.discountAmount)}</strong>
              </div>
            ) : null}
            <div className="table-invoice-grand-total">
              <span>{t("Đã thanh toán")}</span>
              <strong data-money>{formatMoney(invoice.totalAmount)}</strong>
            </div>
          </section>

          <p className="table-e-receipt-footnote">
            {t("Đây là biên lai điện tử mô phỏng cho phiên bàn. Phiên đã kết thúc — quét QR trên bàn khi bạn muốn gọi món lần sau.")}
          </p>
        </div>

        <footer className="table-invoice-modal-actions">
          <button className="is-secondary" onClick={onClose} type="button">
            {t("Đóng")}
          </button>
        </footer>
      </section>
    </div>
  );
}
