import { useEffect, useRef, useState } from "react";
import { useI18n } from "@cmc/i18n";
import { Banknote, QrCode, X } from "lucide-react";
import type { RequestedPaymentMethod } from "../../types";

type Props = {
  onClose: () => void;
  onRequest: (method: RequestedPaymentMethod) => Promise<void>;
};

export function PaymentRequestModal({ onClose, onRequest }: Props) {
  const { t } = useI18n();
  const [method, setMethod] = useState<RequestedPaymentMethod>("COD");
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

  async function submitRequest() {
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setError("");
    try {
      await onRequest(method);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : t("Không gửi được yêu cầu thanh toán."),
      );
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className="payment-request-overlay"
      onClick={(event) => {
        if (event.currentTarget === event.target && !isSubmittingRef.current) onClose();
      }}
    >
      <section
        aria-label={t("Yêu cầu thanh toán")}
        aria-modal="true"
        className="payment-request-modal"
        role="dialog"
      >
        <header className="payment-request-header">
          <div>
            <span className="panel-kicker">{t("Thanh toán tại bàn")}</span>
            <h3>{t("Yêu cầu thanh toán")}</h3>
          </div>
          <button
            aria-label={t("Đóng")}
            className="vietqr-close"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        <p className="payment-request-copy">
          {t("Chọn cách thanh toán. Nhân viên sẽ xác nhận sau khi nhận đủ tiền.")}
        </p>

        <fieldset className="payment-request-options">
          <legend>{t("Phương thức thanh toán")}</legend>
          <label className={method === "COD" ? "is-selected" : ""}>
            <input
              aria-label={t("Tiền mặt")}
              checked={method === "COD"}
              name="payment-method"
              onChange={() => setMethod("COD")}
              ref={firstOptionRef}
              type="radio"
            />
            <Banknote aria-hidden="true" size={22} />
            <span>
              <strong>{t("Tiền mặt")}</strong>
              <small>{t("Nhân viên đến bàn thu tiền")}</small>
            </span>
          </label>
          <label className={method === "VietQR" ? "is-selected" : ""}>
            <input
              aria-label="VietQR"
              checked={method === "VietQR"}
              name="payment-method"
              onChange={() => setMethod("VietQR")}
              type="radio"
            />
            <QrCode aria-hidden="true" size={22} />
            <span>
              <strong>VietQR</strong>
              <small>{t("Quét mã bằng ứng dụng ngân hàng")}</small>
            </span>
          </label>
        </fieldset>

        {error ? <p className="cmc-inline-error" role="alert">{error}</p> : null}

        <footer className="payment-request-actions">
          <button className="cmc-secondary-link" disabled={isSubmitting} onClick={onClose} type="button">
            {t("Để sau")}
          </button>
          <button className="cmc-payment-request-submit" disabled={isSubmitting} onClick={submitRequest} type="button">
            {isSubmitting ? t("Đang gửi...") : t("Gửi yêu cầu")}
          </button>
        </footer>
      </section>
    </div>
  );
}
