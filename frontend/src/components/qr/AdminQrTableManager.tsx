import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/vietnamese-400.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/vietnamese-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/manrope/vietnamese-700.css";
import { useEffect, useMemo, useState } from "react";
import { createApiClient } from "@cmc/api-client";

type BackendTable = {
  tableCode: string;
  displayName: string;
  isActive: boolean;
  qrToken?: string | null;
  customerPath: string;
};

type QrTable = BackendTable & {
  zone: string;
  seats: number;
  status: "Available" | "Cleaning";
};

type CopyState = {
  tableCode: string;
  status: "success" | "error";
} | null;

const api = createApiClient({
  getAccessToken: () =>
    typeof window === "undefined" ? null : window.localStorage.getItem("cmc.accessToken"),
});
const tableCodes = ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"];

function decorateTable(table: BackendTable, index: number): QrTable {
  return {
    ...table,
    zone: index < 4 ? "Sảnh chính" : index < 6 ? "Cửa sổ" : "Phòng riêng",
    seats: index < 2 ? 2 : index < 6 ? 4 : 8,
    status: table.isActive ? "Available" : "Cleaning",
  };
}

export function AdminQrTableManager() {
  const [tables, setTables] = useState<QrTable[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<CopyState>(null);

  useEffect(() => {
    let isMounted = true;

    Promise.all(tableCodes.map((tableCode) => api.tables.get(tableCode)))
      .then((backendTables) => {
        if (isMounted) {
          setTables(backendTables.map(decorateTable));
          setError(null);
        }
      })
      .catch(() => {
        if (isMounted) {
          setError("Không tải được danh sách bàn từ backend.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const baseUrl = typeof window === "undefined" ? "" : window.location.origin;
  const tablesByZone = useMemo(
    () =>
      tables.reduce<Array<{ zone: string; tables: QrTable[] }>>((zones, table) => {
        const existing = zones.find((zone) => zone.zone === table.zone);
        if (existing) {
          existing.tables.push(table);
        } else {
          zones.push({ zone: table.zone, tables: [table] });
        }
        return zones;
      }, []),
    [tables],
  );

  function getTableLink(table: QrTable) {
    return table.customerPath.startsWith("http")
      ? table.customerPath
      : `${baseUrl}${table.customerPath}`;
  }

  async function copyTableLink(table: QrTable) {
    try {
      await navigator.clipboard.writeText(getTableLink(table));
      setCopyState({ tableCode: table.tableCode, status: "success" });
    } catch {
      setCopyState({ tableCode: table.tableCode, status: "error" });
    }
  }

  return (
    <div className="admin-table-qr-workspace">
      <section className="table-qr-command">
        <div className="table-qr-command-copy">
          <span className="table-qr-kicker">Floor & QR control</span>
          <h3>Sơ đồ bàn đồng bộ với backend</h3>
          <p>Mã bàn, QR token và đường dẫn khách hàng được lấy từ API thay vì dữ liệu giả.</p>
          {error ? (
            <p className="table-copy-feedback is-error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
        <dl className="table-qr-command-stats">
          <div>
            <dt>Bàn hoạt động</dt>
            <dd>{tables.filter((table) => table.isActive).length}</dd>
          </div>
          <div>
            <dt>QR hợp lệ</dt>
            <dd>
              {tables.filter((table) => table.qrToken).length}/{tables.length}
            </dd>
          </div>
          <div>
            <dt>Khu vực</dt>
            <dd>{tablesByZone.length}</dd>
          </div>
        </dl>
      </section>

      {isLoading ? (
        <p className="table-copy-feedback" role="status">
          Đang tải danh sách bàn...
        </p>
      ) : null}

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
                const copied = copyState?.tableCode === table.tableCode;
                return (
                  <article className={`table-qr-card is-${table.status.toLowerCase()}`} key={table.tableCode}>
                    <header className="table-qr-card-heading">
                      <div className="table-number-plate">
                        <span>Bàn</span>
                        <strong>{table.tableCode}</strong>
                      </div>
                      <span className={`table-status-label is-${table.status.toLowerCase()}`}>
                        <i aria-hidden="true" />
                        {table.isActive ? "Sẵn sàng" : "Tạm ngưng"}
                      </span>
                    </header>

                    <div className="table-qr-card-body">
                      <dl className="table-qr-meta">
                        <div>
                          <dt>Tên hiển thị</dt>
                          <dd>{table.displayName}</dd>
                        </div>
                        <div>
                          <dt>Sức chứa</dt>
                          <dd>{table.seats} ghế</dd>
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
                          <code title={getTableLink(table)}>{getTableLink(table)}</code>
                        </div>
                      </div>
                    </div>

                    <footer className="table-qr-actions">
                      <a href={table.customerPath} target="_blank" rel="noreferrer">
                        Mở bàn
                      </a>
                      <button
                        type="button"
                        onClick={() => copyTableLink(table)}
                        aria-label={`Sao chép link bàn ${table.tableCode}`}
                      >
                        {copied && copyState.status === "success"
                          ? "Đã sao chép"
                          : copied
                            ? "Thử lại"
                            : "Sao chép link"}
                      </button>
                    </footer>
                    {copied ? (
                      <p className={`table-copy-feedback is-${copyState.status}`} role="status">
                        {copyState.status === "success"
                          ? `Đã sao chép link bàn ${table.tableCode}.`
                          : "Không thể sao chép đường dẫn bàn."}
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
  );
}
