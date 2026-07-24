import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/vietnamese-400.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/vietnamese-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/manrope/vietnamese-700.css";
import { useEffect, useState } from "react";
import { TableQrCode } from "./TableQrCode";
import { api } from "../../services/apiClient";
import type { AdminTable } from "@cmc/shared-types";
import { buildOrderingLink } from "../../utils/tableOrderingLink";

type CopyState = {
  tableCode: string;
  status: "success" | "error";
} | null;

// QR-bearing table data is loaded from the Admin-only GET /api/admin/tables endpoint.

export function AdminQrTableManager({ embedded = false }: { embedded?: boolean }) {
  const [tables, setTables] = useState<AdminTable[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<CopyState>(null);

  useEffect(() => {
    let isMounted = true;

    api.tables.listAdmin()
      .then((response) => {
        if (isMounted) {
          setTables(response.items);
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

  async function copyTableLink(table: AdminTable) {
    try {
      await navigator.clipboard.writeText(buildOrderingLink(table));
      setCopyState({ tableCode: table.tableCode, status: "success" });
    } catch {
      setCopyState({ tableCode: table.tableCode, status: "error" });
    }
  }

  const activeCount = tables.filter((table) => table.isActive).length;
  const qrCount = tables.filter((table) => table.qrToken).length;

  return (
    <div className="admin-table-qr-workspace">
      {!embedded ? (
        <section className="table-qr-command">
          <div className="table-qr-command-copy">
            <span className="table-qr-kicker">QR table control</span>
            <h3>Bàn và mã QR từ backend</h3>
            <p>
              Mỗi link bàn luôn trỏ về ứng dụng đặt món. Admin chỉ quản lý và sao chép
              link, khách phải mở phiên bàn bằng QR trước khi đặt món.
            </p>
            {error ? (
              <p className="table-copy-feedback is-error" role="alert">
                {error}
              </p>
            ) : null}
          </div>
          <dl className="table-qr-command-stats">
            <div>
              <dt>Bàn hoạt động</dt>
              <dd>{activeCount}</dd>
            </div>
            <div>
              <dt>QR hợp lệ</dt>
              <dd>
                {qrCount}/{tables.length}
              </dd>
            </div>
            <div>
              <dt>Nguồn dữ liệu</dt>
              <dd>API</dd>
            </div>
          </dl>
        </section>
      ) : error ? (
        <div className="ops-notice ops-notice--danger">{error}</div>
      ) : null}

      {isLoading ? (
        <p className="table-copy-feedback" role="status">
          Đang tải danh sách bàn...
        </p>
      ) : null}

      <div className="table-zone-grid table-zone-grid-flat">
        {tables.map((table) => {
          const copied = copyState?.tableCode === table.tableCode;
          const orderingLink = buildOrderingLink(table);

          return (
            <article
              className={`table-qr-card is-${table.isActive ? "available" : "cleaning"}`}
              key={table.tableCode}
            >
              <header className="table-qr-card-heading">
                <div className="table-number-plate">
                  <span>Bàn</span>
                  <strong>{table.tableCode}</strong>
                </div>
                <span className={`table-status-label is-${table.isActive ? "available" : "cleaning"}`}>
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
                    <dt>QR token</dt>
                    <dd>{table.qrToken ? "Đã cấu hình" : "Chưa có"}</dd>
                  </div>
                </dl>
                <div className="table-qr-asset">
                  <TableQrCode
                    downloadName={`qr-ban-${table.tableCode}.png`}
                    label={`QR bàn ${table.tableCode}`}
                    value={orderingLink}
                  />
                  <div className="table-qr-link-copy">
                    <span>Link ứng dụng đặt món</span>
                    <code title={orderingLink}>{orderingLink}</code>
                  </div>
                </div>
              </div>

              <footer className="table-qr-actions">
                <a href={orderingLink} target="_blank" rel="noreferrer">
                  Mở trang khách
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
    </div>
  );
}
