import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReportSummaryResponse } from "@cmc/shared-types";
import { api } from "../../services/apiClient";
import { BarChart3, Download } from "lucide-react";
import "../../components/operations/operations.css";

type RangePreset = "today" | "7d" | "30d" | "custom";

function formatVnd(value: number): string {
  return `${value.toLocaleString("vi-VN")}đ`;
}

function toDateInput(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function endOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
}

function getPresetRange(preset: RangePreset): { from: string; to: string } {
  const today = new Date();
  if (preset === "today") {
    return { from: toDateInput(today), to: toDateInput(today) };
  }
  if (preset === "7d") {
    const from = new Date(today);
    from.setDate(today.getDate() - 6);
    return { from: toDateInput(from), to: toDateInput(today) };
  }
  if (preset === "30d") {
    const from = new Date(today);
    from.setDate(today.getDate() - 29);
    return { from: toDateInput(from), to: toDateInput(today) };
  }
  const from = new Date(today);
  from.setDate(today.getDate() - 29);
  return { from: toDateInput(from), to: toDateInput(today) };
}

function downloadCsv(filename: string, rows: string[][]) {
  const content = rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([`\uFEFF${content}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function RevenueChart({ dailyRevenue }: { dailyRevenue: ReportSummaryResponse["dailyRevenue"] }) {
  if (dailyRevenue.length === 0) {
    return <div className="ops-empty">Chưa có dữ liệu doanh thu theo ngày</div>;
  }

  const maxRevenue = Math.max(...dailyRevenue.map((day) => day.revenue), 1);
  const width = 640;
  const height = 220;
  const padding = 24;
  const barGap = 8;
  const barWidth = Math.max(12, (width - padding * 2 - barGap * (dailyRevenue.length - 1)) / dailyRevenue.length);

  return (
    <div className="ops-reports-chart" aria-label="Biểu đồ doanh thu theo ngày">
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        {dailyRevenue.map((day, index) => {
          const barHeight = (day.revenue / maxRevenue) * (height - padding * 2);
          const x = padding + index * (barWidth + barGap);
          const y = height - padding - barHeight;
          return (
            <g key={day.date}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                rx="4"
                fill="var(--color-primary, #2563eb)"
              >
                <title>{`${day.date}: ${formatVnd(day.revenue)}`}</title>
              </rect>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function AdminReportsPage() {
  const [report, setReport] = useState<ReportSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [preset, setPreset] = useState<RangePreset>("30d");
  const initialRange = getPresetRange("30d");
  const [from, setFrom] = useState(initialRange.from);
  const [to, setTo] = useState(initialRange.to);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await api.reports.summary({
        from: startOfDay(new Date(`${from}T00:00:00`)).toISOString(),
        to: endOfDay(new Date(`${to}T00:00:00`)).toISOString(),
      });
      setReport(data);
    } catch {
      setError("Không tải được báo cáo.");
    } finally {
      setIsLoading(false);
    }
  }, [from, to]);

  useEffect(() => {
    void load();
  }, [load]);

  function applyPreset(nextPreset: RangePreset) {
    setPreset(nextPreset);
    if (nextPreset === "custom") return;
    const range = getPresetRange(nextPreset);
    setFrom(range.from);
    setTo(range.to);
  }

  const paidRate = useMemo(() => {
    if (!report || report.totalOrders === 0) return "0%";
    return `${Math.round((report.paidOrders / report.totalOrders) * 100)}%`;
  }, [report]);

  const topItemsWithShare = useMemo(() => {
    if (!report) return [];
    const total = report.topItems.reduce((sum, item) => sum + item.revenue, 0) || 1;
    return report.topItems.map((item) => ({
      ...item,
      share: Math.round((item.revenue / total) * 100),
    }));
  }, [report]);

  function exportCsv() {
    if (!report) return;
    downloadCsv(`bao-cao-${from}-${to}.csv`, [
      ["Loại", "Giá trị"],
      ["Tổng đơn", String(report.totalOrders)],
      ["Đơn đã thanh toán", String(report.paidOrders)],
      ["Doanh thu gộp", String(report.grossRevenue)],
      ["Tổng giảm giá", String(report.totalDiscount)],
      ["Doanh thu thực", String(report.netRevenue)],
      [],
      ["Ngày", "Số đơn", "Doanh thu"],
      ...report.dailyRevenue.map((day) => [day.date, String(day.orderCount), String(day.revenue)]),
      [],
      ["Món", "Số lượng", "Doanh thu"],
      ...report.topItems.map((item) => [item.name, String(item.quantitySold), String(item.revenue)]),
    ]);
  }

  return (
    <div>
      <div className="ops-page-header">
        <h1>Báo cáo doanh thu</h1>
        <p>Tổng hợp doanh thu, món bán chạy và xu hướng theo ngày.</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}

      <div className="ops-reports-toolbar">
        {([
          ["today", "Hôm nay"],
          ["7d", "7 ngày"],
          ["30d", "30 ngày"],
          ["custom", "Tùy chọn"],
        ] as Array<[RangePreset, string]>).map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={`ops-btn ops-btn--sm ${preset === value ? "ops-btn--primary" : "ops-btn--ghost"}`}
            onClick={() => applyPreset(value)}
          >
            {label}
          </button>
        ))}
        {preset === "custom" ? (
          <>
            <div className="ops-form-group" style={{ margin: 0 }}>
              <label className="ops-form-label">Từ ngày</label>
              <input className="ops-form-input" type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
            </div>
            <div className="ops-form-group" style={{ margin: 0 }}>
              <label className="ops-form-label">Đến ngày</label>
              <input className="ops-form-input" type="date" value={to} onChange={(event) => setTo(event.target.value)} />
            </div>
          </>
        ) : null}
        <button className="ops-btn ops-btn--primary ops-btn--sm" type="button" onClick={() => void load()}>Xem báo cáo</button>
        <button className="ops-btn ops-btn--ghost ops-btn--sm" disabled={!report} type="button" onClick={exportCsv}>
          <Download size={14} aria-hidden="true" /> Xuất CSV
        </button>
      </div>

      {isLoading ? (
        <div className="ops-empty"><div className="ops-empty-icon"><BarChart3 aria-hidden="true" /></div>Đang tải...</div>
      ) : report ? (
        <>
          <div className="ops-stats">
            <div className="ops-stat-card">
              <div className="ops-stat-label">Tổng đơn</div>
              <div className="ops-stat-value">{report.totalOrders}</div>
              <div className="ops-stat-detail">Trong khoảng đã chọn</div>
            </div>
            <div className="ops-stat-card">
              <div className="ops-stat-label">Đơn đã thanh toán</div>
              <div className="ops-stat-value">{report.paidOrders}</div>
              <div className="ops-stat-detail">Tỷ lệ {paidRate}</div>
            </div>
            <div className="ops-stat-card">
              <div className="ops-stat-label">Doanh thu gộp</div>
              <div className="ops-stat-value" style={{ fontSize: 22 }}>{formatVnd(report.grossRevenue)}</div>
              <div className="ops-stat-detail">Trước giảm giá</div>
            </div>
            <div className="ops-stat-card">
              <div className="ops-stat-label">Tổng giảm giá</div>
              <div className="ops-stat-value" style={{ fontSize: 22 }}>{formatVnd(report.totalDiscount)}</div>
              <div className="ops-stat-detail">Khuyến mãi áp dụng</div>
            </div>
            <div className="ops-stat-card">
              <div className="ops-stat-label">Doanh thu thực</div>
              <div className="ops-stat-value" style={{ fontSize: 22 }}>{formatVnd(report.netRevenue)}</div>
              <div className="ops-stat-detail">Sau giảm giá</div>
            </div>
          </div>

          <div className="ops-page-header"><h2>Doanh thu theo ngày</h2></div>
          <RevenueChart dailyRevenue={report.dailyRevenue} />

          <div className="ops-page-header"><h2>Món bán chạy</h2></div>
          <table className="ops-table">
            <thead>
              <tr>
                <th>Món</th>
                <th>Số lượng</th>
                <th>Doanh thu</th>
                <th>Đóng góp</th>
              </tr>
            </thead>
            <tbody>
              {topItemsWithShare.map((item) => (
                <tr key={item.menuItemId}>
                  <td><strong>{item.name}</strong></td>
                  <td>{item.quantitySold}</td>
                  <td>{formatVnd(item.revenue)}</td>
                  <td>{item.share}%</td>
                </tr>
              ))}
              {topItemsWithShare.length === 0 ? (
                <tr><td colSpan={4}><div className="ops-empty">Chưa có dữ liệu</div></td></tr>
              ) : null}
            </tbody>
          </table>

          <div className="ops-page-header" style={{ marginTop: 24 }}><h2>Chi tiết theo ngày</h2></div>
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
