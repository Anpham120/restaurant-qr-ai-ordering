import { useEffect, useMemo, useState } from "react";
import { AdminStatusBadge } from "../components/admin/AdminStatusBadge";
import { VietQrPaymentModal } from "../components/customer/VietQrPaymentModal";
import { failOrderPayment } from "../services/adminOrderService";
import {
  confirmOrderPayment,
  getKitchenOrders,
  isAwaitingPayment,
  isRefundable,
  refundOrderPayment,
} from "../services/orderService";
import type { OrderTrackingOrder } from "../types";
import { PageShell } from "./PageShell";

const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;
const REFUND_NOTE_MAX = 500;

function tableLabel(order: OrderTrackingOrder): string {
  return order.tableCode ? `Bàn ${order.tableCode}` : "Chưa có bàn";
}

function isCollected(order: OrderTrackingOrder): boolean {
  return (
    order.paymentStatus === "Confirmed" ||
    order.paymentStatus === "Paid" ||
    order.paymentStatus === "Refunded"
  );
}

export function StaffPaymentsPage() {
  const [orders, setOrders] = useState<OrderTrackingOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [qrOrderCode, setQrOrderCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [refundCode, setRefundCode] = useState<string | null>(null);
  const [refundNote, setRefundNote] = useState("");

  async function reload() {
    const data = await getKitchenOrders();
    setOrders(data);
  }

  useEffect(() => {
    reload()
      .catch(() => setError("Không tải được danh sách thanh toán."))
      .finally(() => setIsLoading(false));
  }, []);

  const awaiting = useMemo(() => orders.filter(isAwaitingPayment), [orders]);
  const collected = useMemo(() => orders.filter(isCollected), [orders]);

  const stats = useMemo(() => {
    if (isLoading) {
      return [
        { label: "Đơn chờ thu", value: "...", detail: "Đang tải" },
        { label: "Tổng cần thu", value: "...", detail: "Đang tải" },
        { label: "Đã thu / hoàn", value: "...", detail: "Đang tải" },
      ];
    }

    const total = awaiting.reduce((sum, order) => sum + order.totalAmount, 0);
    const refunded = collected.filter((order) => order.paymentStatus === "Refunded").length;
    const paid = collected.length - refunded;
    return [
      { label: "Đơn chờ thu", value: String(awaiting.length), detail: "Chưa xác nhận thanh toán" },
      { label: "Tổng cần thu", value: formatCurrency(total), detail: "Cộng dồn đơn chờ thu" },
      { label: "Đã thu / hoàn", value: `${paid} / ${refunded}`, detail: "Đã xác nhận và đã hoàn tiền" },
    ];
  }, [awaiting, collected, isLoading]);

  async function runAction(
    orderCode: string,
    action: () => Promise<unknown>,
    message: string,
    onSuccess?: () => void,
  ) {
    setPendingCode(orderCode);
    setNotice(null);
    try {
      await action();
      await reload();
      setNotice(message);
      onSuccess?.();
    } catch {
      setNotice("Thao tác thất bại. Thử lại.");
    } finally {
      setPendingCode(null);
    }
  }

  function openRefund(orderCode: string) {
    setRefundCode(orderCode);
    setRefundNote("");
  }

  function closeRefund() {
    setRefundCode(null);
    setRefundNote("");
  }

  return (
    <PageShell
      eyebrow="Staff"
      title="Thu ngân"
      description="Xác nhận, từ chối hoặc hoàn tiền cho các đơn tại bàn. Dữ liệu lấy trực tiếp từ backend."
      variant="staff"
      stats={stats}
    >
      <div className="staff-workspace">
        {notice ? <p className="staff-payment-notice">{notice}</p> : null}

        {error ? (
          <p>{error}</p>
        ) : isLoading ? (
          <p>Đang tải danh sách thanh toán...</p>
        ) : awaiting.length === 0 && collected.length === 0 ? (
          <p className="realtime-empty">Không có đơn thanh toán nào.</p>
        ) : (
          <>
            {awaiting.length > 0 ? (
              <div className="staff-payment-group">
                <h3 className="staff-section-title">Đơn chờ thu</h3>
                <section className="staff-board" aria-label="Đơn chờ thanh toán">
                  {awaiting.map((order) => (
                    <article className="staff-ticket" key={order.orderId}>
                      <div className="staff-ticket-meta">
                        <span>{order.orderCode}</span>
                        <strong>{tableLabel(order)}</strong>
                        <small>{order.paymentMethod}</small>
                      </div>
                      <p>
                        <AdminStatusBadge status={order.paymentStatus} />{" "}
                        <strong>{formatCurrency(order.totalAmount)}</strong>
                      </p>
                      <div className="staff-action-row">
                        <button
                          className="button primary"
                          type="button"
                          disabled={pendingCode === order.orderCode}
                          onClick={() =>
                            runAction(
                              order.orderCode,
                              () => confirmOrderPayment(order.orderCode, "Thu tại bàn"),
                              `Đã xác nhận thu đơn ${order.orderCode}.`,
                            )
                          }
                        >
                          Xác nhận thu
                        </button>
                        <button
                          className="button"
                          type="button"
                          disabled={pendingCode === order.orderCode}
                          onClick={() =>
                            runAction(
                              order.orderCode,
                              () => failOrderPayment(order.orderCode, "Từ chối tại bàn"),
                              `Đã từ chối thanh toán đơn ${order.orderCode}.`,
                            )
                          }
                        >
                          Từ chối
                        </button>
                        {order.paymentMethod === "VietQR" ? (
                          <button className="button" type="button" onClick={() => setQrOrderCode(order.orderCode)}>
                            Hiện QR
                          </button>
                        ) : null}
                      </div>
                    </article>
                  ))}
                </section>
              </div>
            ) : null}

            {collected.length > 0 ? (
              <div className="staff-payment-group">
                <h3 className="staff-section-title">Đã thu &amp; hoàn tiền</h3>
                <section className="staff-board" aria-label="Đơn đã thu và hoàn tiền">
                  {collected.map((order) => (
                    <article className="staff-ticket" key={order.orderId}>
                      <div className="staff-ticket-meta">
                        <span>{order.orderCode}</span>
                        <strong>{tableLabel(order)}</strong>
                        <small>{order.paymentMethod}</small>
                      </div>
                      <p>
                        <AdminStatusBadge status={order.paymentStatus} />{" "}
                        <strong>{formatCurrency(order.totalAmount)}</strong>
                      </p>
                      {isRefundable(order) ? (
                        refundCode === order.orderCode ? (
                          <div className="staff-refund-confirm">
                            <label>
                              Lý do hoàn tiền (tùy chọn)
                              <input
                                maxLength={REFUND_NOTE_MAX}
                                onChange={(event) => setRefundNote(event.target.value)}
                                placeholder="Ví dụ: Khách trả món"
                                type="text"
                                value={refundNote}
                              />
                            </label>
                            <p className="staff-refund-warning">
                              Hoàn tiền sẽ đảo trạng thái thanh toán và không thể hoàn tác.
                            </p>
                            <div className="staff-action-row">
                              <button
                                className="button danger"
                                type="button"
                                disabled={pendingCode === order.orderCode}
                                onClick={() =>
                                  runAction(
                                    order.orderCode,
                                    () => refundOrderPayment(order.orderCode, refundNote.trim() || undefined),
                                    `Đã hoàn tiền đơn ${order.orderCode}.`,
                                    closeRefund,
                                  )
                                }
                              >
                                Xác nhận hoàn tiền
                              </button>
                              <button
                                className="button"
                                type="button"
                                disabled={pendingCode === order.orderCode}
                                onClick={closeRefund}
                              >
                                Hủy
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="staff-action-row">
                            <button className="button" type="button" onClick={() => openRefund(order.orderCode)}>
                              Hoàn tiền
                            </button>
                          </div>
                        )
                      ) : null}
                    </article>
                  ))}
                </section>
              </div>
            ) : null}
          </>
        )}
      </div>

      {qrOrderCode ? (
        <VietQrPaymentModal
          orderCode={qrOrderCode}
          onClose={() => setQrOrderCode(null)}
          onPaymentConfirmed={() => {
            const confirmedCode = qrOrderCode;
            setQrOrderCode(null);
            setNotice(`Đơn ${confirmedCode} đã thanh toán.`);
            reload().catch(() => undefined);
          }}
        />
      ) : null}
    </PageShell>
  );
}
