import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Banknote, CheckCircle2, QrCode, ReceiptText } from "lucide-react";
import type {
  OrderTrackingOrder,
  TableInvoice,
  TableInvoicePaymentRequest,
  TableInvoicePaymentRequestResponse,
} from "../types";
import {
  getTableInvoice,
  getTableSessionOrders,
  requestTableInvoicePayment,
} from "../services/orderService";
import { useOrderingSession } from "./OrderingSessionProvider";
import { TableInvoicePaymentModal } from "./TableInvoicePaymentModal";

const itemStatusLabel: Record<string, string> = {
  Pending: "Chờ xác nhận",
  Preparing: "Đang chuẩn bị",
  Ready: "Sẵn sàng phục vụ",
  Served: "Đã phục vụ",
  Cancelled: "Đã hủy",
};

const formatVnd = (amount: number) => `${amount.toLocaleString("vi-VN")}đ`;

export function SessionOrdersPage() {
  const { context } = useOrderingSession();
  const [orders, setOrders] = useState<OrderTrackingOrder[]>([]);
  const [invoice, setInvoice] = useState<TableInvoice | null>(null);
  const [paymentResult, setPaymentResult] = useState<TableInvoicePaymentRequestResponse | null>(null);
  const [showPaymentRequest, setShowPaymentRequest] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadOrders() {
    setLoading(true);
    setError("");
    try {
      const [nextOrders, nextInvoice] = await Promise.all([
        getTableSessionOrders(context.sessionId, context.sessionToken),
        getTableInvoice(context.sessionId, context.sessionToken),
      ]);
      setOrders(nextOrders);
      setInvoice(nextInvoice);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể tải các món đã gọi.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePaymentRequest(payload: TableInvoicePaymentRequest) {
    const result = await requestTableInvoicePayment(
      context.sessionId,
      context.sessionToken,
      payload,
    );
    setInvoice(result.invoice);
    setPaymentResult(result);
    setShowPaymentRequest(false);
  }

  useEffect(() => { void loadOrders(); }, [context.sessionId, context.sessionToken]);

  if (loading) return <section className="ordering-page"><p>Đang tải hóa đơn phiên bàn…</p></section>;

  const canRequestPayment = Boolean(
    invoice &&
    invoice.orderRounds.length > 0 &&
    !["Pending", "Paid", "Confirmed"].includes(invoice.status),
  );
  const isPending = invoice?.status === "Pending";
  const isPaid = invoice?.status === "Paid" || invoice?.status === "Confirmed";
  const vietQr = paymentResult?.vietQr ?? invoice?.vietQr ?? null;

  return (
    <section className="ordering-page" aria-labelledby="session-orders-title">
      <header className="ordering-page-heading">
        <div><p>Phiên bàn {context.tableCode}</p><h1 id="session-orders-title">Món đã gọi</h1></div>
        <button type="button" onClick={() => void loadOrders()}>Làm mới</button>
      </header>

      {error ? <div className="ordering-inline-error" role="alert"><p>{error}</p><button type="button" onClick={() => void loadOrders()}>Thử lại</button></div> : null}

      {!error && invoice ? (
        <section className={`table-invoice-summary ${isPending ? "is-pending" : ""} ${isPaid ? "is-paid" : ""}`} aria-labelledby="table-invoice-title">
          <div className="table-invoice-summary-heading">
            <div><ReceiptText aria-hidden="true" size={22} /><span><small>Hóa đơn toàn phiên</small><strong id="table-invoice-title">{invoice.orderRounds.length} lần gọi món</strong></span></div>
            <strong>{formatVnd(invoice.totalAmount)}</strong>
          </div>
          <p>Mã ưu đãi, tích điểm và thanh toán được áp dụng một lần cho toàn bộ món trong phiên bàn.</p>

          {canRequestPayment ? <button className="table-invoice-pay-button" onClick={() => setShowPaymentRequest(true)} type="button">Yêu cầu thanh toán</button> : null}
          {isPending && invoice.method === "COD" ? <div className="table-invoice-status"><Banknote aria-hidden="true" size={20} /><span><strong>Đang chờ thanh toán tiền mặt</strong><small>Nhân viên sẽ đến bàn để thu tiền và xác nhận hóa đơn.</small></span></div> : null}
          {isPending && invoice.method === "VietQR" ? <div className="table-invoice-status"><QrCode aria-hidden="true" size={20} /><span><strong>Đang chờ thanh toán VietQR</strong><small>Chuyển đúng số tiền và nội dung trên mã QR.</small></span></div> : null}
          {isPaid ? <div className="table-invoice-status"><CheckCircle2 aria-hidden="true" size={20} /><span><strong>Hóa đơn đã thanh toán</strong><small>Cảm ơn bạn đã dùng bữa tại CMC Restaurant.</small></span></div> : null}

          {vietQr ? (
            <div className="table-invoice-vietqr" role="status">
              <img alt={`Mã VietQR cho hóa đơn ${vietQr.invoiceCode}`} src={vietQr.qrImageDataUri} />
              <div><small>Nội dung chuyển khoản</small><strong>{vietQr.transferContent}</strong><span>{formatVnd(vietQr.amount)}</span></div>
            </div>
          ) : null}
        </section>
      ) : null}

      {!error && orders.length === 0 ? (
        <div className="ordering-empty"><p>Bàn chưa có lần gọi món nào trong phiên này.</p><Link to="../menu">Quay lại thực đơn</Link></div>
      ) : null}

      <div className="ordering-orders-list">
        {orders.map((order) => (
          <article className="ordering-order-card" key={order.orderId}>
            <header>
              <div><strong>{order.orderCode}</strong><span>{new Date(order.createdAt).toLocaleString("vi-VN")}</span></div>
              <Link to={order.orderCode}>Chi tiết</Link>
            </header>
            <ul>
              {order.items.map((item) => (
                <li key={item.orderItemId}><span>{item.quantity}× {item.name}</span><em>{itemStatusLabel[item.status] ?? item.status}</em></li>
              ))}
            </ul>
            <footer><span>Trạng thái: {order.status}</span><strong>{formatVnd(order.subtotalAmount)}</strong></footer>
          </article>
        ))}
      </div>

      {showPaymentRequest && invoice ? (
        <TableInvoicePaymentModal invoice={invoice} onClose={() => setShowPaymentRequest(false)} onRequest={handlePaymentRequest} />
      ) : null}
    </section>
  );
}
