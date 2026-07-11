import { useEffect, useMemo, useState } from "react";
import { getKitchenOrders, isRefundable, refundOrderPayment } from "../services/orderService";
import type { OrderTrackingOrder } from "../types";
import { Printer, ReceiptText, X } from "lucide-react";
import "../components/operations/operations.css";

type FilterTab = "all" | "pending" | "confirmed" | "refunded";
const FILTER_LABELS: Record<FilterTab, string> = {
  all: "Tất cả",
  pending: "Chờ thanh toán",
  confirmed: "Đã thanh toán",
  refunded: "Đã hoàn tiền",
};

const formatVnd = (v: number) => v.toLocaleString("vi-VN") + "đ";
function formatDate(d?: string) { return d ? new Date(d).toLocaleString("vi-VN") : "-"; }

function matchesFilter(o: OrderTrackingOrder, f: FilterTab) {
  if (f === "all") return true;
  if (f === "pending") return o.paymentStatus === "Pending" || o.paymentStatus === "Failed";
  if (f === "confirmed") return o.paymentStatus === "Confirmed" || o.paymentStatus === "Paid";
  if (f === "refunded") return o.paymentStatus === "Refunded";
  return true;
}

export function AdminInvoicesPage() {
  const [orders, setOrders] = useState<OrderTrackingOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<FilterTab>("all");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<OrderTrackingOrder | null>(null);
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [refundNote, setRefundNote] = useState("");

  async function reload() {
    const data = await getKitchenOrders();
    setOrders(data);
  }

  useEffect(() => {
    reload().catch(() => setError("Không tải được hóa đơn.")).finally(() => setIsLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return orders
      .filter((o) => matchesFilter(o, filter))
      .filter((o) => !q || o.orderCode.toLowerCase().includes(q) || (o.tableCode ?? "").toLowerCase().includes(q))
      .sort((a, b) => new Date(b.createdAt ?? 0).getTime() - new Date(a.createdAt ?? 0).getTime());
  }, [orders, filter, search]);

  const stats = useMemo(() => {
    const paid = orders.filter((o) => o.paymentStatus === "Confirmed" || o.paymentStatus === "Paid");
    const revenue = paid.reduce((s, o) => s + o.totalAmount, 0);
    const refunded = orders.filter((o) => o.paymentStatus === "Refunded").length;
    return [
      { label: "Tổng đơn", value: String(orders.length), detail: "Tất cả hóa đơn" },
      { label: "Doanh thu", value: formatVnd(revenue), detail: `${paid.length} đơn đã thu` },
      { label: "Hoàn tiền", value: String(refunded), detail: "Đơn đã hoàn" },
    ];
  }, [orders]);

  async function handleRefund(code: string) {
    setPending(code);
    try {
      await refundOrderPayment(code, refundNote.trim() || undefined);
      await reload();
      setNotice(`Hoàn tiền ${code}.`);
      setDetail(null);
      setRefundNote("");
    } catch {
      setNotice("Hoàn tiền thất bại.");
    } finally {
      setPending(null);
    }
  }

  if (isLoading) return <div className="ops-empty"><div className="ops-empty-icon"><ReceiptText aria-hidden="true" /></div>Đang tải...</div>;

  return (
    <div>
      <div className="ops-page-header">
        <h1>Hóa đơn</h1>
        <p>Xem tất cả hóa đơn, chi tiết thanh toán và hoàn tiền</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-stats">
        {stats.map((s) => (
          <div className="ops-stat-card" key={s.label}>
            <div className="ops-stat-label">{s.label}</div>
            <div className="ops-stat-value">{s.value}</div>
            <div className="ops-stat-detail">{s.detail}</div>
          </div>
        ))}
      </div>

      <div className="ops-toolbar">
        {(Object.keys(FILTER_LABELS) as FilterTab[]).map((tab) => (
          <button
            key={tab}
            className={`ops-btn ${filter === tab ? "ops-btn--primary" : "ops-btn--ghost"} ops-btn--sm`}
            onClick={() => setFilter(tab)}
            type="button"
          >
            {FILTER_LABELS[tab]}
          </button>
        ))}
        <input className="ops-form-input" placeholder="Tìm mã đơn, bàn..." value={search} onChange={(e) => setSearch(e.target.value)} style={{ width: 200 }} />
      </div>

      <table className="ops-table">
        <thead>
          <tr>
            <th>Mã đơn</th>
            <th>Bàn</th>
            <th>PT</th>
            <th>TT toán</th>
            <th>Tổng tiền</th>
            <th>Ngày</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((o) => (
            <tr key={o.orderId}>
              <td><strong>{o.orderCode}</strong></td>
              <td>{o.tableCode ?? "-"}</td>
              <td>{o.paymentMethod}</td>
              <td><span className={`ops-badge ops-badge--${o.paymentStatus.toLowerCase()}`}>{o.paymentStatus}</span></td>
              <td><strong>{formatVnd(o.totalAmount)}</strong></td>
              <td style={{ fontSize: 12, color: "var(--color-muted)" }}>{formatDate(o.createdAt)}</td>
              <td>
                <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => { setDetail(o); setRefundNote(""); }} type="button">Chi tiết</button>
              </td>
            </tr>
          ))}
          {filtered.length === 0 ? <tr><td colSpan={7}><div className="ops-empty">Không có hóa đơn</div></td></tr> : null}
        </tbody>
      </table>

      {detail ? (
        <div className="ops-modal-overlay" onClick={() => setDetail(null)}>
          <div className="ops-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ops-modal-header">
              <h2>Hóa đơn {detail.orderCode}</h2>
              <button aria-label="Đóng" className="ops-modal-close" onClick={() => setDetail(null)} type="button"><X aria-hidden="true" size={18} /></button>
            </div>
            <div className="ops-modal-body">
              <div className="ops-card-meta" style={{ marginBottom: 12, gap: 8, flexWrap: "wrap" }}>
                {detail.tableCode ? <span className="ops-card-table">Bàn {detail.tableCode}</span> : null}
                <span className={`ops-badge ops-badge--${detail.status.toLowerCase()}`}>{detail.status}</span>
                <span className={`ops-badge ops-badge--${detail.paymentStatus.toLowerCase()}`}>{detail.paymentMethod} · {detail.paymentStatus}</span>
                <span style={{ fontSize: 12, color: "var(--color-muted)" }}>{formatDate(detail.createdAt)}</span>
              </div>
              <div className="ops-item-list">
                {detail.items.map((item) => (
                  <div className="ops-item-row" key={item.orderItemId}>
                    <div className="ops-item-info">
                      <div className="ops-item-name">{item.quantity}× {item.name}</div>
                      <span className="ops-item-qty">{formatVnd(item.unitPrice)} × {item.quantity}</span>
                    </div>
                    <span style={{ fontWeight: 600 }}>{formatVnd(item.unitPrice * item.quantity)}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 12, padding: 12, background: "var(--color-bg-subtle)", borderRadius: 8, fontSize: 16, fontWeight: 700, textAlign: "right" }}>
                Tổng: {formatVnd(detail.totalAmount)}
              </div>

              {isRefundable(detail) ? (
                <div style={{ marginTop: 16 }}>
                  <label className="ops-form-label">Hoàn tiền</label>
                  <input className="ops-form-input" placeholder="Lý do (tùy chọn)" value={refundNote} onChange={(e) => setRefundNote(e.target.value)} maxLength={500} />
                  <button className="ops-btn ops-btn--danger" style={{ marginTop: 8, width: "100%" }} disabled={pending === detail.orderCode} onClick={() => handleRefund(detail.orderCode)} type="button">
                    {pending === detail.orderCode ? "Đang xử lý..." : "Xác nhận hoàn tiền"}
                  </button>
                </div>
              ) : null}

              <button className="ops-btn ops-btn--primary" style={{ width: "100%", marginTop: 12 }} onClick={() => window.print()} type="button">
                <Printer aria-hidden="true" size={15} /> In hóa đơn
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
