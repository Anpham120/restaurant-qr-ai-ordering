import { useEffect, useMemo, useState } from "react";
import type { TableInvoice } from "@cmc/shared-types";
import { listTableInvoices } from "../services/orderService";
import { Printer, ReceiptText, X } from "lucide-react";
import "../components/operations/operations.css";

type FilterTab = "all" | "pending" | "confirmed" | "cancelled";
const FILTER_LABELS: Record<FilterTab, string> = {
  all: "Tất cả",
  pending: "Chờ thanh toán",
  confirmed: "Đã thanh toán",
  cancelled: "Đã hủy yêu cầu",
};
const formatVnd = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

function matchesFilter(invoice: TableInvoice, filter: FilterTab) {
  if (filter === "pending") return invoice.status === "Pending";
  if (filter === "confirmed") return invoice.status === "Confirmed" || invoice.status === "Paid";
  if (filter === "cancelled") return invoice.status === "Cancelled";
  return true;
}

export function AdminInvoicesPanel({ embedded = false }: { embedded?: boolean }) {
  const [invoices, setInvoices] = useState<TableInvoice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<FilterTab>("all");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<TableInvoice | null>(null);

  async function reload() {
    setInvoices(await listTableInvoices());
  }

  useEffect(() => {
    reload().catch(() => setError("Không tải được hóa đơn phiên bàn.")).finally(() => setIsLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return invoices
      .filter((invoice) => matchesFilter(invoice, filter))
      .filter((invoice) => !query ||
        (invoice.invoiceCode ?? "").toLowerCase().includes(query) ||
        (invoice.tableCode ?? "").toLowerCase().includes(query));
  }, [invoices, filter, search]);
  const stats = useMemo(() => {
    const paid = invoices.filter((invoice) => invoice.status === "Confirmed" || invoice.status === "Paid");
    return [
      { label: "Tổng hóa đơn", value: String(invoices.length), detail: "Theo phiên bàn" },
      { label: "Doanh thu", value: formatVnd(paid.reduce((sum, invoice) => sum + invoice.totalAmount, 0)), detail: `${paid.length} phiên đã thu` },
      { label: "Chờ thu", value: String(invoices.filter((invoice) => invoice.status === "Pending").length), detail: "Cần thu ngân xử lý" },
    ];
  }, [invoices]);

  if (isLoading) return <div className="ops-empty"><div className="ops-empty-icon"><ReceiptText aria-hidden="true" /></div>Đang tải...</div>;

  return (
    <div>
      {!embedded ? (
        <div className="ops-page-header"><h1>Hóa đơn phiên bàn</h1><p>Mỗi phiên bàn có một hóa đơn tổng, gồm nhiều lần gọi món</p></div>
      ) : null}
      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      <div className="ops-stats">
        {stats.map((stat) => <div className="ops-stat-card" key={stat.label}><div className="ops-stat-label">{stat.label}</div><div className="ops-stat-value">{stat.value}</div><div className="ops-stat-detail">{stat.detail}</div></div>)}
      </div>
      <div className="ops-toolbar">
        {(Object.keys(FILTER_LABELS) as FilterTab[]).map((tab) => (
          <button className={`ops-btn ${filter === tab ? "ops-btn--primary" : "ops-btn--ghost"} ops-btn--sm`} key={tab} onClick={() => setFilter(tab)} type="button">{FILTER_LABELS[tab]}</button>
        ))}
        <input className="ops-form-input" onChange={(event) => setSearch(event.target.value)} placeholder="Tìm mã hóa đơn, bàn..." style={{ width: 220 }} value={search} />
      </div>
      <div className="ops-card-list">
        {filtered.map((invoice) => (
          <article className="ops-card" key={`card-${invoice.tableSessionId}`}>
            <div className="ops-card-header">
              <span className="ops-card-code">{invoice.invoiceCode ?? "Chưa yêu cầu"}</span>
              <span className="ops-card-table">Bàn {invoice.tableCode ?? "-"}</span>
            </div>
            <div className="ops-card-meta">
              <span className={`ops-badge ops-badge--${invoice.status.toLowerCase()}`}>{invoice.status}</span>
              <strong>{formatVnd(invoice.totalAmount)}</strong>
            </div>
            <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => setDetail(invoice)} type="button">Chi tiết</button>
          </article>
        ))}
      </div>
      <table className="ops-table ops-table-responsive">
        <thead><tr><th>Mã hóa đơn</th><th>Bàn</th><th>Lượt gọi</th><th>Phương thức</th><th>Trạng thái</th><th>Tổng tiền</th><th>Thao tác</th></tr></thead>
        <tbody>
          {filtered.map((invoice) => (
            <tr key={invoice.tableSessionId}>
              <td><strong>{invoice.invoiceCode ?? "Chưa yêu cầu"}</strong></td>
              <td>{invoice.tableCode ?? "-"}</td>
              <td>{invoice.orderRounds.length}</td>
              <td>{invoice.method === "COD" ? "Tiền mặt" : invoice.method === "VietQR" ? "VietQR" : "-"}</td>
              <td><span className={`ops-badge ops-badge--${invoice.status.toLowerCase()}`}>{invoice.status}</span></td>
              <td><strong>{formatVnd(invoice.totalAmount)}</strong></td>
              <td><button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => setDetail(invoice)} type="button">Chi tiết</button></td>
            </tr>
          ))}
          {filtered.length === 0 ? <tr><td colSpan={7}><div className="ops-empty">Không có hóa đơn</div></td></tr> : null}
        </tbody>
      </table>

      {detail ? (
        <div className="ops-modal-overlay" onClick={() => setDetail(null)}>
          <div className="ops-modal" onClick={(event) => event.stopPropagation()}>
            <div className="ops-modal-header"><h2>Hóa đơn {detail.invoiceCode}</h2><button aria-label="Đóng" className="ops-modal-close" onClick={() => setDetail(null)} type="button"><X aria-hidden="true" size={18} /></button></div>
            <div className="ops-modal-body">
              <div className="ops-card-meta" style={{ marginBottom: 12 }}><span className="ops-card-table">Bàn {detail.tableCode}</span><span className={`ops-badge ops-badge--${detail.status.toLowerCase()}`}>{detail.method} · {detail.status}</span></div>
              <p>{detail.orderRounds.length} lần gọi món trong phiên</p>
              <div className="ops-item-list">
                {detail.items.map((item) => <div className="ops-item-row" key={item.menuItemId}><div className="ops-item-info"><div className="ops-item-name">{item.quantity}× {item.name}</div><span className="ops-item-qty">{formatVnd(item.unitPrice)} × {item.quantity}</span></div><strong>{formatVnd(item.lineTotal)}</strong></div>)}
              </div>
              <div style={{ marginTop: 12, padding: 12, background: "var(--color-bg-subtle)", borderRadius: 8 }}>
                <div>Tạm tính: <strong>{formatVnd(detail.subtotalAmount)}</strong></div>
                {detail.discountAmount > 0 ? <div>Ưu đãi {detail.promotionCode}: <strong>-{formatVnd(detail.discountAmount)}</strong></div> : null}
                <div style={{ fontSize: 18, fontWeight: 800, marginTop: 8 }}>Tổng: {formatVnd(detail.totalAmount)}</div>
                {detail.customerPhoneNumber ? <div>Tích điểm: {detail.customerPhoneNumber}</div> : null}
              </div>
              <button className="ops-btn ops-btn--primary" onClick={() => window.print()} style={{ width: "100%", marginTop: 12 }} type="button"><Printer aria-hidden="true" size={15} /> In hóa đơn</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function AdminInvoicesPage() {
  return <AdminInvoicesPanel />;
}
