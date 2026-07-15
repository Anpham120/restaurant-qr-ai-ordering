import { useEffect, useRef, useState } from "react";
import { formatVnd } from "@cmc/brand-ui";
import { getOrderPayment } from "../../services/orderService";
import type { VietQrPaymentResponse, PaymentResponse } from "../../types";
import { CircleCheck, X } from "lucide-react";

type Props = {
  orderCode: string;
  qrData?: VietQrPaymentResponse;
  onClose: () => void;
  onPaymentConfirmed?: () => void;
};

const POLL_INTERVAL = 5000;

export function VietQrPaymentModal({ orderCode, qrData, onClose, onPaymentConfirmed }: Props) {
  const [resolvedQrData, setResolvedQrData] = useState<VietQrPaymentResponse | null>(qrData ?? null);
  const [paymentStatus, setPaymentStatus] = useState<string>(qrData?.paymentStatus ?? "Pending");
  const [isLoading, setIsLoading] = useState(false);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (qrData) {
      setResolvedQrData(qrData);
      setPaymentStatus(qrData.paymentStatus);
      setIsLoading(false);
      return;
    }

    setResolvedQrData(null);
    setPaymentStatus("Pending");
    setIsLoading(false);
  }, [orderCode, qrData]);

  useEffect(() => {
    if (!resolvedQrData || paymentStatus === "Confirmed" || paymentStatus === "Paid") return;

    pollRef.current = window.setInterval(async () => {
      try {
        const payment: PaymentResponse = await getOrderPayment(orderCode);
        setPaymentStatus(payment.status);
        if (payment.status === "Confirmed" || payment.status === "Paid") {
          if (pollRef.current) clearInterval(pollRef.current);
          onPaymentConfirmed?.();
        }
      } catch {
        // silently ignore poll errors
      }
    }, POLL_INTERVAL);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [resolvedQrData, paymentStatus, orderCode, onPaymentConfirmed]);

  const isPaid = paymentStatus === "Confirmed" || paymentStatus === "Paid";

  return (
    <div className="vietqr-overlay" onClick={onClose}>
      <div
        aria-label="Thanh toán VietQR"
        aria-modal="true"
        className="vietqr-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
      >
        <header className="vietqr-modal-header">
          <div>
            <span className="panel-kicker">Thanh toán VietQR</span>
            <h3>{orderCode}</h3>
          </div>
          <button className="vietqr-close" type="button" onClick={onClose} aria-label="Đóng">
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        {isLoading ? (
          <div className="vietqr-loading">Đang tạo mã QR thanh toán...</div>
        ) : resolvedQrData ? (
          <div className="vietqr-content">
            {isPaid ? (
              <div className="vietqr-success">
                <span className="vietqr-success-icon"><CircleCheck aria-hidden="true" /></span>
                <h4>Thanh toán thành công!</h4>
                <p>Đơn hàng {orderCode} đã được xác nhận thanh toán.</p>
                <button className="button primary" type="button" onClick={onClose}>
                  Đóng
                </button>
              </div>
            ) : (
              <>
                <div className="vietqr-qr-section">
                  <img
                    className="vietqr-qr-image"
                    src={resolvedQrData.qrImageDataUri}
                    alt={`QR thanh toán đơn ${orderCode}`}
                  />
                  <p className="vietqr-scan-hint">Quét mã QR bằng app ngân hàng</p>
                </div>

                <div className="vietqr-bank-info">
                  <dl>
                    <div>
                      <dt>Ngân hàng</dt>
                      <dd>{resolvedQrData.bankId}</dd>
                    </div>
                    <div>
                      <dt>Số tài khoản</dt>
                      <dd><code>{resolvedQrData.accountNumber}</code></dd>
                    </div>
                    <div>
                      <dt>Chủ tài khoản</dt>
                      <dd>{resolvedQrData.accountName}</dd>
                    </div>
                    <div>
                      <dt>Số tiền</dt>
          <dd><strong data-money>{formatVnd(resolvedQrData.amount)}</strong></dd>
                    </div>
                    <div>
                      <dt>Nội dung CK</dt>
                      <dd><code>{resolvedQrData.transferContent}</code></dd>
                    </div>
                  </dl>
                </div>

                <div className="vietqr-status-bar">
                  <span className="vietqr-polling-dot" />
                  <span>Đang chờ xác nhận thanh toán...</span>
                </div>
              </>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
