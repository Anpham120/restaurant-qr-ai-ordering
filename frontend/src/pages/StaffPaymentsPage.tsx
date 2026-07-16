import { useCallback, useEffect, useMemo, useState } from "react";
import type { TableInvoice } from "@cmc/shared-types";
import {
  cancelTableInvoicePayment,
  confirmTableInvoicePayment,
  listTableInvoices,
} from "../services/orderService";
import { Banknote, Check, CreditCard, QrCode, RefreshCw, X } from "lucide-react";
import "../components/operations/operations.css";

const formatVnd = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

export function StaffPaymentsPage() {
  const [invoices, setInvoices] = useState<TableInvoice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);

  const loadInvoices = useCallback(async () => {
    try {
      setInvoices(await listTableInvoices());
      setError("");
    } catch {
      setError("Không tải được danh sách hóa đơn phiên bàn.");
    }
  }, []);

  useEffect(() => {
    loadInvoices().finally(() => setIsLoading(false));
  }, [loadInvoices]);

  useEffect(() => {
    const interval = window.setInterval(() => void loadInvoices(), 5_000);
    return () => window.clearInterval(interval);
  }, [loadInvoices]);

  const awaiting = useMemo(
    () => invoices.filter((invoice) => invoice.status === "Pending"),
    [invoices],
  );
  const collected = useMemo(
    () => invoices.filter((invoice) => invoice.status === "Confirmed" || invoice.status === "Paid"),
    [invoices],
  );
  const stats = useMemo(() => [
    { label: "Bàn chờ thu", value: String(awaiting.length), detail: "Hóa đơn toàn phiên" },
    { label: "Tổng cần thu", value: formatVnd(awaiting.reduce((sum, invoice) => sum + invoice.totalAmount, 0)), detail: "Sau ưu đãi" },
    { label: "Đã xác nhận", value: String(collected.length), detail: "Phiên đã đóng" },
  ], [awaiting, collected]);

  async function runAction(sessionId: string, action: () => Promise<unknown>, successMessage: string) {
    setPendingSessionId(sessionId);
    setNotice("");
    try {
      await action();
      await loadInvoices();
      setNotice(successMessage);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "Thao tác thất bại. Thử lại.");
    } finally {
      setPendingSessionId(null);
    }
  }

  if (isLoading) {
    return <div className="ops-empty"><div className="ops-empty-icon"><CreditCard aria-hidden="true" /></div>Đang tải...</div>;
  }

  return (
    <div>
      <div className="ops-page-header">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div><h1>Thu ngân</h1><p>Xác nhận thanh toán cho toàn bộ hóa đơn của phiên bàn</p></div>
          <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => void loadInvoices()} type="button"><RefreshCw aria-hidden="true" size={14} /> Làm mới</button>
        </div>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-stats">
        {stats.map((stat) => (
          <div className="ops-stat-card" key={stat.label}>
            <div className="ops-stat-label">{stat.label}</div>
            <div className="ops-stat-value">{stat.value}</div>
            <div className="ops-stat-detail">{stat.detail}</div>
          </div>
        ))}
      </div>

      {awaiting.length > 0 ? (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Hóa đơn chờ thu ({awaiting.length})</h3>
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))" }}>
            {awaiting.map((invoice) => (
              <article className="ops-card" key={invoice.tableSessionId}>
                <div className="ops-card-header">
                  <span className="ops-card-code">Phiên {invoice.orderRounds.length} lượt gọi</span>
                  <span className="ops-card-table">Bàn {invoice.tableCode}</span>
                </div>
                <div className="ops-card-meta">
                  <span className="ops-badge ops-badge--pending">
                    {invoice.method === "COD" ? <Banknote aria-hidden="true" size={14} /> : <QrCode aria-hidden="true" size={14} />}
                    {invoice.method === "COD" ? "Tiền mặt" : "VietQR"} · Chờ thu
                  </span>
                  <strong>{formatVnd(invoice.totalAmount)}</strong>
                </div>
                <div className="ops-card-items">
                  {invoice.items.map((item) => <span className="ops-card-item-chip" key={item.menuItemId}>{item.quantity}× {item.name}</span>)}
                </div>
                {invoice.promotionCode ? <p>Ưu đãi: <strong>{invoice.promotionCode}</strong> (-{formatVnd(invoice.discountAmount)})</p> : null}
                {invoice.customerPhoneNumber ? <p>Tích điểm: <strong>{invoice.customerPhoneNumber}</strong></p> : null}
                <div className="ops-card-actions">
                  <button
                    className="ops-btn ops-btn--success ops-btn--sm"
                    disabled={pendingSessionId === invoice.tableSessionId}
                    onClick={() => void runAction(invoice.tableSessionId, () => confirmTableInvoicePayment(invoice.tableSessionId, "Thu ngân xác nhận đã thu đủ."), `Đã thanh toán bàn ${invoice.tableCode}`)}
                    type="button"
                  ><Check aria-hidden="true" size={14} /> Xác nhận thu</button>
                  <button
                    className="ops-btn ops-btn--ghost ops-btn--sm"
                    disabled={pendingSessionId === invoice.tableSessionId}
                    onClick={() => void runAction(invoice.tableSessionId, () => cancelTableInvoicePayment(invoice.tableSessionId, "Hủy yêu cầu để bàn tiếp tục gọi món."), `Đã hủy yêu cầu bàn ${invoice.tableCode}`)}
                    type="button"
                  ><X aria-hidden="true" size={14} /> Hủy yêu cầu</button>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : <div className="ops-empty" style={{ padding: 24 }}>Không có hóa đơn chờ thu</div>}

      {collected.length > 0 ? (
        <section>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Đã thu ({collected.length})</h3>
          <table className="ops-table">
            <thead><tr><th>Bàn</th><th>Số lượt gọi</th><th>Phương thức</th><th>Tổng tiền</th><th>Trạng thái</th></tr></thead>
            <tbody>
              {collected.map((invoice) => (
                <tr key={invoice.tableSessionId}>
                  <td><strong>{invoice.tableCode}</strong></td>
                  <td>{invoice.orderRounds.length}</td>
                  <td>{invoice.method === "COD" ? "Tiền mặt" : "VietQR"}</td>
                  <td>{formatVnd(invoice.totalAmount)}</td>
                  <td><span className="ops-badge ops-badge--confirmed">Đã xác nhận</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  );
}
