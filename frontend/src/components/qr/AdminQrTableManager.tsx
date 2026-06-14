import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/vietnamese-400.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/vietnamese-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/manrope/vietnamese-700.css";
import { useMemo, useState } from "react";

type QrTable = {
  tableCode: string;
  zone: string;
  seats: number;
  status: "Available" | "Serving" | "Cleaning";
  currentOrder?: string;
};

type CopyState = {
  tableCode: string;
  status: "success" | "error";
} | null;

const tables: QrTable[] = [
  { tableCode: "T-01", zone: "Sảnh chính", seats: 2, status: "Available" },
  { tableCode: "T-02", zone: "Sảnh chính", seats: 4, status: "Serving", currentOrder: "ORDER-008" },
  { tableCode: "T-03", zone: "Sảnh chính", seats: 4, status: "Available" },
  { tableCode: "T-04", zone: "Cửa sổ", seats: 2, status: "Cleaning" },
  { tableCode: "T05", zone: "Cửa sổ", seats: 6, status: "Serving", currentOrder: "ORDER-001" },
  { tableCode: "T-06", zone: "Phòng riêng", seats: 8, status: "Available" },
];

const statusLabels: Record<QrTable["status"], string> = {
  Available: "Sẵn sàng",
  Serving: "Đang phục vụ",
  Cleaning: "Đang dọn",
};

const statusDescriptions: Record<QrTable["status"], string> = {
  Available: "Có thể nhận khách",
  Serving: "Đang có đơn tại bàn",
  Cleaning: "Chờ hoàn tất vệ sinh",
};

export function AdminQrTableManager() {
  const [copyState, setCopyState] = useState<CopyState>(null);

  const baseUrl = useMemo(() => {
    if (typeof window === "undefined") {
      return "";
    }

    return window.location.origin;
  }, []);

  const tablesByZone = useMemo(() => {
    return tables.reduce<Array<{ zone: string; tables: QrTable[] }>>((zones, table) => {
      const currentZone = zones.find((zone) => zone.zone === table.zone);

      if (currentZone) {
        currentZone.tables.push(table);
      } else {
        zones.push({ zone: table.zone, tables: [table] });
      }

      return zones;
    }, []);
  }, []);

  const statusCounts = {
    Available: tables.filter((table) => table.status === "Available").length,
    Serving: tables.filter((table) => table.status === "Serving").length,
    Cleaning: tables.filter((table) => table.status === "Cleaning").length,
  };

  async function handleCopy(tableCode: string) {
    const link = `${baseUrl}/table/${tableCode}`;

    try {
      await navigator.clipboard.writeText(link);
      setCopyState({ tableCode, status: "success" });
    } catch {
      setCopyState({ tableCode, status: "error" });
    }
  }

  return (
    <div className="admin-table-qr-workspace">
      <section className="table-qr-command" aria-labelledby="table-qr-command-title">
        <div className="table-qr-command-copy">
          <span className="table-qr-kicker">Floor & QR control</span>
          <h3 id="table-qr-command-title">Sơ đồ bàn cho một ca phục vụ liền mạch</h3>
          <p>
            Theo dõi trạng thái phòng ăn, kiểm tra đường dẫn QR và mở nhanh trải
            nghiệm gọi món của từng bàn từ cùng một màn hình.
          </p>
        </div>
        <dl className="table-qr-command-stats" aria-label="Tổng quan bàn trong ca">
          <div>
            <dt>Bàn hoạt động</dt>
            <dd>{tables.length}</dd>
          </div>
          <div>
            <dt>QR hợp lệ</dt>
            <dd>{tables.length}/{tables.length}</dd>
          </div>
          <div>
            <dt>Khu vực</dt>
            <dd>{tablesByZone.length}</dd>
          </div>
        </dl>
      </section>

      <div className="table-qr-layout">
        <aside className="table-qr-sidebar" aria-label="Chú giải và cấu hình QR">
          <section className="table-qr-legend">
            <div className="table-qr-sidebar-heading">
              <span className="table-qr-kicker">Live floor</span>
              <h3>Trạng thái phòng ăn</h3>
            </div>
            <ul>
              {(Object.keys(statusLabels) as QrTable["status"][]).map((status) => (
                <li key={status}>
                  <span className={`table-status-dot is-${status.toLowerCase()}`} aria-hidden="true" />
                  <div>
                    <strong>{statusLabels[status]}</strong>
                    <small>{statusDescriptions[status]}</small>
                  </div>
                  <b>{statusCounts[status]}</b>
                </li>
              ))}
            </ul>
          </section>

          <section className="table-qr-route-note">
            <span className="table-qr-kicker">QR route</span>
            <code>/table/:tableCode</code>
            <p>Mỗi mã mở đúng thực đơn và giữ mã bàn xuyên suốt giỏ hàng.</p>
          </section>
        </aside>

        <div className="table-zone-list">
          {tablesByZone.map((zone) => (
            <section className="table-zone" key={zone.zone} aria-label={`Khu vực ${zone.zone}`}>
              <header className="table-zone-heading">
                <div>
                  <span className="table-qr-kicker">Khu vực</span>
                  <h3>{zone.zone}</h3>
                </div>
                <span>{zone.tables.length} bàn</span>
              </header>

              <div className="table-zone-grid">
                {zone.tables.map((table) => {
                  const tableLink = `${baseUrl}/table/${table.tableCode}`;
                  const copySucceeded = copyState?.tableCode === table.tableCode && copyState.status === "success";
                  const copyFailed = copyState?.tableCode === table.tableCode && copyState.status === "error";

                  return (
                    <article
                      className={`table-qr-card is-${table.status.toLowerCase()}`}
                      key={table.tableCode}
                    >
                      <header className="table-qr-card-heading">
                        <div className="table-number-plate">
                          <span>Bàn</span>
                          <strong>{table.tableCode}</strong>
                        </div>
                        <span className={`table-status-label is-${table.status.toLowerCase()}`}>
                          <i aria-hidden="true" />
                          {statusLabels[table.status]}
                        </span>
                      </header>

                      <div className="table-qr-card-body">
                        <dl className="table-qr-meta">
                          <div>
                            <dt>Sức chứa</dt>
                            <dd>{table.seats} ghế</dd>
                          </div>
                          <div>
                            <dt>Đơn hiện tại</dt>
                            <dd>{table.currentOrder ?? "Chưa có đơn"}</dd>
                          </div>
                        </dl>

                        <div className="table-qr-asset">
                          <div className="table-qr-preview" aria-label={`QR bàn ${table.tableCode}`}>
                            <i className="finder top-left" aria-hidden="true" />
                            <i className="finder top-right" aria-hidden="true" />
                            <i className="finder bottom-left" aria-hidden="true" />
                            <span>{table.tableCode}</span>
                          </div>
                          <div className="table-qr-link-copy">
                            <span>Đường dẫn bàn</span>
                            <code title={tableLink}>{tableLink}</code>
                          </div>
                        </div>
                      </div>

                      <footer className="table-qr-actions">
                        <a href={`/table/${table.tableCode}`} target="_blank" rel="noreferrer">
                          Mở bàn
                          <span aria-hidden="true">↗</span>
                        </a>
                        <button
                          type="button"
                          onClick={() => handleCopy(table.tableCode)}
                          aria-label={`Sao chép link bàn ${table.tableCode}`}
                        >
                          {copySucceeded ? "Đã sao chép" : copyFailed ? "Thử lại" : "Sao chép link"}
                        </button>
                      </footer>
                      {copyState?.tableCode === table.tableCode ? (
                        <p className={`table-copy-feedback is-${copyState.status}`} role="status">
                          {copySucceeded
                            ? `Đã sao chép link bàn ${table.tableCode}.`
                            : "Không thể sao chép. Hãy kiểm tra quyền truy cập clipboard."}
                        </p>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
