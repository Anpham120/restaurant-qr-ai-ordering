import { useEffect, useRef, useState } from "react";
import { generateVietQrPayment, getOrderPayment } from "../../services/orderService";
import type { VietQrPaymentResponse, PaymentResponse } from "../../types";

type Props = {
  orderCode: string;
  onClose: () => void;
  onPaymentConfirmed?: () => void;
};

const POLL_INTERVAL = 5000;

export function VietQrPaymentModal({ orderCode, onClose, onPaymentConfirmed }: Props) {
  const [qrData, setQrData] = useState<VietQrPaymentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<string>("Pending");
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    generateVietQrPayment(orderCode)
      .then((data) => {
        setQrData(data);
        setPaymentStatus(data.paymentStatus);
      })
      .catch(() => setError("Không tạo được mã QR thanh toán."))
      .finally(() => setIsLoading(false));

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [orderCode]);

  useEffect(() => {
    if (!qrData || paymentStatus === "Confirmed" || paymentStatus === "Paid") return;

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
  }, [qrData, paymentStatus, orderCode, onPaymentConfirmed]);

  const isPaid = paymentStatus === "Confirmed" || paymentStatus === "Paid";

  return (
    <div className="vietqr-overlay" onClick={onClose}>
      <div className="vietqr-modal" onClick={(e) => e.stopPropagation()}>
        <header className="vietqr-modal-header">
          <div>
            <span className="panel-kicker">Thanh toán VietQR</span>
            <h3>{orderCode}</h3>
          </div>
          <button className="vietqr-close" type="button" onClick={onClose} aria-label="Đóng">
            ✕
          </button>
        </header>

        {isLoading ? (
          <div className="vietqr-loading">
            <p>Đang tạo mã QR thanh toán...</p>
          </div>
        ) : error ? (
          <div className="vietqr-error">
            <p>{error}</p>
            <button className="button" type="button" onClick={onClose}>
              Đóng
            </button>
          </div>
        ) : qrData ? (
          <div className="vietqr-content">
            {isPaid ? (
              <div className="vietqr-success">
                <span className="vietqr-success-icon">✓</span>
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
                    src={qrData.qrImageDataUri}
                    alt={`QR thanh toán đơn ${orderCode}`}
                  />
                  <p className="vietqr-scan-hint">Quét mã QR bằng app ngân hàng</p>
                </div>

                <div className="vietqr-bank-info">
                  <dl>
                    <div>
                      <dt>Ngân hàng</dt>
                      <dd>{qrData.bankId}</dd>
                    </div>
                    <div>
                      <dt>Số tài khoản</dt>
                      <dd><code>{qrData.accountNumber}</code></dd>
                    </div>
                    <div>
                      <dt>Chủ tài khoản</dt>
                      <dd>{qrData.accountName}</dd>
                    </div>
                    <div>
                      <dt>Số tiền</dt>
                      <dd><strong>{qrData.amount.toLocaleString("vi-VN")}đ</strong></dd>
                    </div>
                    <div>
                      <dt>Nội dung CK</dt>
                      <dd><code>{qrData.transferContent}</code></dd>
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
