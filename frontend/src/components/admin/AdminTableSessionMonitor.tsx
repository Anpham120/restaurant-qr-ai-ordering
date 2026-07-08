import { useCallback, useEffect, useMemo, useState } from "react";
import type { AdminTableSessionSummary, Table } from "@cmc/shared-types";
import { ApiError, createApiClient } from "@cmc/api-client";
import "../operations/operations.css";
import "./admin-table-sessions.css";

const api = createApiClient({
  getAccessToken: () =>
    typeof window === "undefined" ? null : window.localStorage.getItem("cmc.accessToken"),
});

const REFRESH_INTERVAL_MS = 15000;

type TableFilter = "all" | "serving" | "free";

type TableWithSession = {
  table: Table;
  session: AdminTableSessionSummary | null;
};

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function formatRelativeMinutes(value: string) {
  const diffMs = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(diffMs / 60000));
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  return `${hours} giờ ${minutes % 60} phút trước`;
}

export function AdminTableSessionMonitor() {
  const [tables, setTables] = useState<Table[]>([]);
  const [sessions, setSessions] = useState<AdminTableSessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState<TableFilter>("all");
  const [closingId, setClosingId] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const [tableList, sessionList] = await Promise.all([
        api.tables.list(),
        api.tables.listAdminSessions(),
      ]);
      setTables(tableList.items);
      setSessions(sessionList.items);
      setError("");
      setLastUpdatedAt(new Date());
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setError("Bạn cần đăng nhập với quyền Nhân viên hoặc Quản trị viên để xem phiên bàn.");
      } else {
        setError("Không tải được dữ liệu phiên bàn từ máy chủ.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  // Với mỗi bàn, lấy phiên Open mới nhất (chưa hết hạn) nếu có.
  const rows: TableWithSession[] = useMemo(() => {
    const openByTable = new Map<string, AdminTableSessionSummary>();
    for (const session of sessions) {
      if (session.status !== "Open" || session.isExpired) continue;
      const existing = openByTable.get(session.tableCode);
      if (!existing || new Date(session.openedAt) > new Date(existing.openedAt)) {
        openByTable.set(session.tableCode, session);
      }
    }
    return tables.map((table) => ({
      table,
      session: openByTable.get(table.tableCode) ?? null,
    }));
  }, [tables, sessions]);

  const servingCount = rows.filter((r) => r.session).length;
  const activeOrderTotal = rows.reduce((sum, r) => sum + (r.session?.activeOrderCount ?? 0), 0);

  const visibleRows = rows.filter((row) => {
    if (filter === "serving") return row.session !== null;
    if (filter === "free") return row.session === null;
    return true;
  });

  async function handleCloseSession(session: AdminTableSessionSummary) {
    if (!confirm(`Đóng phiên bàn ${session.tableCode}? Khách sẽ phải quét QR lại để đặt món.`)) return;
    setClosingId(session.sessionId);
    try {
      await api.tables.closeSession(session.sessionId);
      setNotice(`Đã đóng phiên bàn ${session.tableCode}.`);
      await load();
    } catch {
      setNotice(`Không đóng được phiên bàn ${session.tableCode}. Vui lòng thử lại.`);
    } finally {
      setClosingId(null);
    }
  }

  if (isLoading) {
    return <div className="ops-empty"><div className="ops-empty-icon">🪑</div>Đang tải phiên bàn...</div>;
  }

  return (
    <div>
      <div className="ops-page-header">
        <h1>Phiên bàn</h1>
        <p>Theo dõi {tables.length} bàn theo thời gian thực — bàn nào đang phục vụ, bàn nào trống</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-stats">
        <div className="ops-stat-card">
          <div className="ops-stat-label">Tổng số bàn</div>
          <div className="ops-stat-value">{tables.length}</div>
        </div>
        <div className="ops-stat-card">
          <div className="ops-stat-label">Đang phục vụ</div>
          <div className="ops-stat-value ts-value--serving">{servingCount}</div>
        </div>
        <div className="ops-stat-card">
          <div className="ops-stat-label">Bàn trống</div>
          <div className="ops-stat-value">{tables.length - servingCount}</div>
        </div>
        <div className="ops-stat-card">
          <div className="ops-stat-label">Đơn đang xử lý</div>
          <div className="ops-stat-value ts-value--orders">{activeOrderTotal}</div>
        </div>
      </div>

      <div className="ops-toolbar">
        <div className="ts-filter-chips" role="tablist" aria-label="Lọc bàn">
          {([
            ["all", `Tất cả (${rows.length})`],
            ["serving", `Đang phục vụ (${servingCount})`],
            ["free", `Trống (${rows.length - servingCount})`],
          ] as Array<[TableFilter, string]>).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`ts-chip${filter === value ? " active" : ""}`}
              onClick={() => setFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
        {lastUpdatedAt ? (
          <span className="ts-last-updated">
            Cập nhật lúc {lastUpdatedAt.toLocaleTimeString("vi-VN")} · tự làm mới mỗi 15 giây
          </span>
        ) : null}
      </div>

      <div className="ts-grid">
        {visibleRows.map(({ table, session }) => (
          <article
            key={table.tableCode}
            className={`ts-card${session ? " ts-card--serving" : ""}${!table.isActive ? " ts-card--inactive" : ""}`}
          >
            <header className="ts-card-head">
              <div className="ts-table-plate">
                <span>Bàn</span>
                <strong>{table.tableCode}</strong>
              </div>
              <span className={`ts-status${session ? " is-serving" : " is-free"}`}>
                {!table.isActive ? "Tạm ngưng" : session ? "Đang phục vụ" : "Trống"}
              </span>
            </header>

            {session ? (
              <div className="ts-card-body">
                <dl className="ts-meta">
                  <div>
                    <dt>Mở phiên</dt>
                    <dd>{formatTime(session.openedAt)} · {formatRelativeMinutes(session.openedAt)}</dd>
                  </div>
                  <div>
                    <dt>Hết hạn</dt>
                    <dd>{formatTime(session.expiresAt)}</dd>
                  </div>
                  <div>
                    <dt>Đơn đang xử lý</dt>
                    <dd>
                      <strong className={session.activeOrderCount > 0 ? "ts-order-count" : ""}>
                        {session.activeOrderCount}
                      </strong>
                    </dd>
                  </div>
                </dl>
                <button
                  type="button"
                  className="ops-btn ops-btn--danger ops-btn--sm"
                  disabled={closingId === session.sessionId}
                  onClick={() => handleCloseSession(session)}
                >
                  {closingId === session.sessionId ? "Đang đóng..." : "Đóng phiên"}
                </button>
              </div>
            ) : (
              <div className="ts-card-body ts-card-body--free">
                <p>Chưa có khách. Khách quét QR trên bàn để mở phiên và đặt món.</p>
              </div>
            )}
          </article>
        ))}
        {visibleRows.length === 0 ? (
          <div className="ops-empty" style={{ gridColumn: "1 / -1" }}>Không có bàn nào khớp bộ lọc</div>
        ) : null}
      </div>
    </div>
  );
}
