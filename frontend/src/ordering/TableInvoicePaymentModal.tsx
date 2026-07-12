import { useEffect, useRef, useState } from "react";
import { Banknote, QrCode, ReceiptText, X } from "lucide-react";
import { validatePromotion } from "../services/orderService";
import type {
  RequestedPaymentMethod,
  TableInvoice,
  TableInvoicePaymentRequest,
} from "../types";
import {
  getInvoicePaymentTotal,
  validateAppliedPromotion,
  type PromotionPreview,
} from "./tableInvoicePaymentModel";

type Props = {
  invoice: TableInvoice;
  onClose: () => void;
  onRequest: (payload: TableInvoicePaymentRequest) => Promise<void>;
};

const formatVnd = (amount: number) => `${amount.toLocaleString("vi-VN")}đ`;

export function TableInvoicePaymentModal({ invoice, onClose, onRequest }: Props) {
  const [method, setMethod] = useState<RequestedPaymentMethod>("COD");
  const [promotionCode, setPromotionCode] = useState("");
  const [customerPhoneNumber, setCustomerPhoneNumber] = useState("");
  const [promotionPreview, setPromotionPreview] = useState<PromotionPreview | null>(null);
  const [isApplyingPromotion, setIsApplyingPromotion] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const isSubmittingRef = useRef(false);
  const firstOptionRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstOptionRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isSubmittingRef.current) onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  async function applyPromotion() {
    const code = promotionCode.trim().toUpperCase();
    if (!code) {
      setPromotionPreview(null);
      setError("");
      return;
    }
    setIsApplyingPromotion(true);
    setError("");
    try {
      const preview = await validatePromotion(code, invoice.subtotalAmount);
      setPromotionCode(preview.code);
      setPromotionPreview(preview);
    } catch (caughtError) {
      setPromotionPreview(null);
      setError(caughtError instanceof Error ? caughtError.message : "Mã ưu đãi không hợp lệ.");
    } finally {
      setIsApplyingPromotion(false);
    }
  }

  async function submitRequest() {
    if (isSubmittingRef.current) return;
    const normalizedPromotionCode = promotionCode.trim().toUpperCase();
    const promotionError = validateAppliedPromotion(promotionCode, promotionPreview);
    if (promotionError) {
      setError(promotionError);
      return;
    }
    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setError("");
    try {
      await onRequest({
        method,
        promotionCode: normalizedPromotionCode || null,
        customerPhoneNumber: customerPhoneNumber.trim() || null,
      });
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Không gửi được yêu cầu thanh toán.");
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  }

  const discountAmount = promotionPreview?.discountAmount ?? 0;
  const totalAmount = getInvoicePaymentTotal(invoice, promotionPreview);

  return (
    <div
      className="table-invoice-overlay"
      onClick={(event) => {
        if (event.currentTarget === event.target && !isSubmittingRef.current) onClose();
      }}
    >
      <section aria-labelledby="table-invoice-payment-title" aria-modal="true" className="table-invoice-modal" role="dialog">
        <header className="table-invoice-modal-header">
          <div>
            <span>Hóa đơn phiên bàn {invoice.tableCode}</span>
            <h2 id="table-invoice-payment-title">Yêu cầu thanh toán</h2>
          </div>
          <button aria-label="Đóng" disabled={isSubmitting} onClick={onClose} type="button"><X aria-hidden="true" size={20} /></button>
        </header>

        <div className="table-invoice-modal-body">
          <section className="table-invoice-receipt" aria-label="Tóm tắt hóa đơn">
            <div className="table-invoice-receipt-title"><ReceiptText aria-hidden="true" size={20} /><strong>{invoice.orderRounds.length} lần gọi món</strong></div>
            <ul>
              {invoice.items.map((item) => (
                <li key={item.menuItemId}><span>{item.quantity}× {item.name}</span><strong>{formatVnd(item.lineTotal)}</strong></li>
              ))}
            </ul>
            <div className="table-invoice-total-row"><span>Tạm tính</span><strong>{formatVnd(invoice.subtotalAmount)}</strong></div>
            {discountAmount > 0 ? <div className="table-invoice-discount-row"><span>Ưu đãi {promotionPreview?.code}</span><strong>-{formatVnd(discountAmount)}</strong></div> : null}
            <div className="table-invoice-grand-total"><span>Cần thanh toán</span><strong>{formatVnd(totalAmount)}</strong></div>
          </section>

          <section className="table-invoice-fields" aria-label="Ưu đãi và tích điểm">
            <label>
              <span>Mã ưu đãi <small>(tùy chọn)</small></span>
              <div className="table-invoice-promotion-input">
                <input
                  onChange={(event) => { setPromotionCode(event.target.value); setPromotionPreview(null); }}
                  placeholder="Ví dụ: GIAM10"
                  value={promotionCode}
                />
                <button disabled={isApplyingPromotion || isSubmitting} onClick={() => void applyPromotion()} type="button">
                  {isApplyingPromotion ? "Đang kiểm tra" : "Áp dụng"}
                </button>
              </div>
            </label>
            <label>
              <span>Số điện thoại tích điểm <small>(tùy chọn)</small></span>
              <input
                inputMode="tel"
                onChange={(event) => setCustomerPhoneNumber(event.target.value)}
                placeholder="0909xxxxxx"
                value={customerPhoneNumber}
              />
            </label>
          </section>

          <fieldset className="table-invoice-methods">
            <legend>Phương thức thanh toán</legend>
            <label className={method === "COD" ? "is-selected" : ""}>
              <input checked={method === "COD"} name="invoice-payment-method" onChange={() => setMethod("COD")} ref={firstOptionRef} type="radio" />
              <Banknote aria-hidden="true" size={22} /><span><strong>Tiền mặt</strong><small>Nhân viên đến bàn thu tiền</small></span>
            </label>
            <label className={method === "VietQR" ? "is-selected" : ""}>
              <input checked={method === "VietQR"} name="invoice-payment-method" onChange={() => setMethod("VietQR")} type="radio" />
              <QrCode aria-hidden="true" size={22} /><span><strong>VietQR</strong><small>Quét mã bằng ứng dụng ngân hàng</small></span>
            </label>
          </fieldset>

          {error ? <p className="ordering-inline-error" role="alert">{error}</p> : null}
        </div>

        <footer className="table-invoice-modal-actions">
          <button className="is-secondary" disabled={isSubmitting} onClick={onClose} type="button">Để sau</button>
          <button disabled={isSubmitting} onClick={() => void submitRequest()} type="button">{isSubmitting ? "Đang gửi..." : `Thanh toán ${formatVnd(totalAmount)}`}</button>
        </footer>
      </section>
    </div>
  );
}
