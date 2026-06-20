import { useEffect, useMemo, useState } from "react";
import { AdminStatusBadge } from "../components/admin/AdminStatusBadge";
import { VietQrPaymentModal } from "../components/customer/VietQrPaymentModal";
import { failOrderPayment } from "../services/adminOrderService";
import { confirmOrderPayment, getKitchenOrders, isAwaitingPayment } from "../services/orderService";
import type { OrderTrackingOrder } from "../types";
import { PageShell } from "./PageShell";

const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

function tableLabel(order: OrderTrackingOrder): string {
  if (order.tableCode) return `Bàn ${order.tableCode}`;
  return order.deliveryInfo?.recipientName ?? "Khách mang về";
}

export function StaffPaymentsPage() {
  const [orders, setOrders] = useState<OrderTrackingOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [qrOrderCode, setQrOrderCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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

  const stats = useMemo(() => {
    if (isLoading) {
      return [
        { label: "Đơn chờ thu", value: "…", detail: "Đang tải" },
        { label: "Tổng cần thu", value: "…", detail: "Đang tải" },
        { label: "VietQR / COD", value: "…", detail: "Đang tải" },
      ];
    }
    const total = awaiting.reduce((sum, order) => sum + order.totalAmount, 0);
    const vietqr = awaiting.filter((order) => order.paymentMethod === "VietQR").length;
    const cod = awaiting.filter((order) => order.paymentMethod === "COD").length;
    return [
      { label: "Đơn chờ thu", value: String(awaiting.length), detail: "Chưa xác nhận thanh toán" },
      { label: "Tổng cần thu", value: formatCurrency(total), detail: "Cộng dồn đơn chờ thu" },
      { label: "VietQR / COD", value: `${vietqr} / ${cod}`, detail: "Phân loại theo phương thức" },
    ];
  }, [awaiting, isLoading]);

  async function runAction(orderCode: string, action: () => Promise<unknown>, message: string) {
    setPendingCode(orderCode);
    setNotice(null);
    try {
      await action();
      await reload();
      setNotice(message);
    } catch {
      setNotice("Thao tác thất bại. Thử lại.");
    } finally {
      setPendingCode(null);
    }
  }

  return (
    <PageShell
      eyebrow="Staff"
      title="Thu ngân"
      description="Xác nhận hoặc từ chối thanh toán cho các đơn đã phục vụ. Dữ liệu lấy trực tiếp từ backend."
      variant="staff"
      stats={stats}
    >
      <div className="staff-workspace">
        {notice ? <p className="staff-payment-notice">{notice}</p> : null}

        {error ? (
          <p>{error}</p>
        ) : isLoading ? (
          <p>Đang tải danh sách thanh toán...</p>
        ) : awaiting.length === 0 ? (
          <p className="realtime-empty">Không có đơn nào chờ thu tiền.</p>
        ) : (
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
                        () => confirmOrderPayment(order.orderCode, "Thu tại quầy"),
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
                        () => failOrderPayment(order.orderCode, "Từ chối tại quầy"),
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
