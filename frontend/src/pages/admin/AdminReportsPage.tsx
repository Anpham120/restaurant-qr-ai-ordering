import { useCallback, useEffect, useState } from "react";
import type { ReportSummaryResponse } from "@cmc/shared-types";
import { api } from "../../services/apiClient";
import { BarChart3 } from "lucide-react";
import "../../components/operations/operations.css";

function formatVnd(value: number): string {
  return `${value.toLocaleString("vi-VN")}đ`;
}

function toDateInput(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export function AdminReportsPage() {
  const [report, setReport] = useState<ReportSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [from, setFrom] = useState(() => toDateInput(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)));
  const [to, setTo] = useState(() => toDateInput(new Date()));

  const load = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await api.reports.summary({
        from: new Date(`${from}T00:00:00`).toISOString(),
        to: new Date(`${to}T23:59:59`).toISOString(),
      });
      setReport(data);
    } catch {
      setError("Không tải được báo cáo.");
    } finally {
      setIsLoading(false);
    }
  }, [from, to]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <div className="ops-page-header">
        <h1>Báo cáo doanh thu</h1>
        <p>Tổng hợp doanh thu, món bán chạy và doanh thu theo ngày</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}

      <div className="ops-toolbar" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div className="ops-form-group" style={{ margin: 0 }}>
          <label className="ops-form-label">Từ ngày</label>
          <input className="ops-form-input" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div className="ops-form-group" style={{ margin: 0 }}>
          <label className="ops-form-label">Đến ngày</label>
          <input className="ops-form-input" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
        <button className="ops-btn ops-btn--primary" type="button" onClick={load}>Xem báo cáo</button>
      </div>

      {isLoading ? (
        <div className="ops-empty"><div className="ops-empty-icon"><BarChart3 aria-hidden="true" /></div>Đang tải...</div>
      ) : report ? (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 24 }}>
            <StatCard label="Tổng đơn" value={String(report.totalOrders)} />
            <StatCard label="Đơn đã thanh toán" value={String(report.paidOrders)} />
            <StatCard label="Doanh thu gộp" value={formatVnd(report.grossRevenue)} />
            <StatCard label="Tổng giảm giá" value={formatVnd(report.totalDiscount)} />
            <StatCard label="Doanh thu thực" value={formatVnd(report.netRevenue)} highlight />
          </div>

          <div className="ops-page-header"><h2>Món bán chạy</h2></div>
          <table className="ops-table">
            <thead>
              <tr>
                <th>Món</th>
                <th>Số lượng</th>
                <th>Doanh thu</th>
              </tr>
            </thead>
            <tbody>
              {report.topItems.map((item) => (
                <tr key={item.menuItemId}>
                  <td><strong>{item.name}</strong></td>
                  <td>{item.quantitySold}</td>
                  <td>{formatVnd(item.revenue)}</td>
                </tr>
              ))}
              {report.topItems.length === 0 ? (
                <tr><td colSpan={3}><div className="ops-empty">Chưa có dữ liệu</div></td></tr>
              ) : null}
            </tbody>
          </table>

          <div className="ops-page-header" style={{ marginTop: 24 }}><h2>Doanh thu theo ngày</h2></div>
          <table className="ops-table">
            <thead>
              <tr>
                <th>Ngày</th>
                <th>Số đơn</th>
                <th>Doanh thu</th>
              </tr>
            </thead>
            <tbody>
              {report.dailyRevenue.map((day) => (
                <tr key={day.date}>
                  <td>{day.date}</td>
                  <td>{day.orderCount}</td>
                  <td>{formatVnd(day.revenue)}</td>
                </tr>
              ))}
              {report.dailyRevenue.length === 0 ? (
                <tr><td colSpan={3}><div className="ops-empty">Chưa có dữ liệu</div></td></tr>
              ) : null}
            </tbody>
          </table>
        </>
      ) : null}
    </div>
  );
}

function StatCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div
      style={{
        background: highlight ? "var(--color-primary, #2563eb)" : "var(--color-surface, #fff)",
        color: highlight ? "#fff" : "inherit",
        border: "1px solid var(--color-border, #e5e7eb)",
        borderRadius: 12,
        padding: 16,
      }}
    >
      <div style={{ fontSize: 13, opacity: 0.8 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}
