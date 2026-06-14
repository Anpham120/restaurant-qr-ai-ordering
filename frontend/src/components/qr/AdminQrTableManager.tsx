import { useMemo, useState } from "react";

type QrTable = {
  tableCode: string;
  zone: string;
  seats: number;
  status: "Available" | "Serving" | "Cleaning";
  currentOrder?: string;
};

const tables: QrTable[] = [
  { tableCode: "T-01", zone: "Sảnh chính", seats: 2, status: "Available" },
  { tableCode: "T-02", zone: "Sảnh chính", seats: 4, status: "Serving", currentOrder: "ORD-1008" },
  { tableCode: "T-03", zone: "Sảnh chính", seats: 4, status: "Available" },
  { tableCode: "T-04", zone: "Cửa sổ", seats: 2, status: "Cleaning" },
  { tableCode: "T-05", zone: "Cửa sổ", seats: 6, status: "Serving", currentOrder: "ORD-1009" },
  { tableCode: "T-06", zone: "Phòng riêng", seats: 8, status: "Available" },
];

const statusLabels: Record<QrTable["status"], string> = {
  Available: "Sẵn sàng",
  Serving: "Đang phục vụ",
  Cleaning: "Đang dọn",
};

export function AdminQrTableManager() {
  const [copiedTable, setCopiedTable] = useState<string | null>(null);

  const baseUrl = useMemo(() => {
    if (typeof window === "undefined") {
      return "";
    }

    return window.location.origin;
  }, []);

  const activeCount = tables.filter((table) => table.status === "Serving").length;
  const availableCount = tables.filter((table) => table.status === "Available").length;

  async function handleCopy(tableCode: string) {
    const link = `${baseUrl}/table/${tableCode}`;

    try {
      await navigator.clipboard.writeText(link);
      setCopiedTable(tableCode);
    } catch {
      setCopiedTable(null);
    }
  }

  return (
    <div className="admin-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">QR management</span>
          <h3>{tables.length} bàn có link QR hợp lệ</h3>
          <p>
            Tất cả link dùng đúng route <strong>/table/:tableCode</strong>, sẵn sàng gắn
            QR library hoặc in ra thẻ bàn khi triển khai thật.
          </p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{availableCount} bàn trống</span>
          <span>{activeCount} đang phục vụ</span>
        </div>
      </section>

      <section className="qr-management-grid" aria-label="Danh sách QR theo bàn">
        {tables.map((table) => {
          const tableLink = `${baseUrl}/table/${table.tableCode}`;

          return (
            <article className="qr-table-card" key={table.tableCode}>
              <div className="qr-preview-block" aria-label={`QR preview ${table.tableCode}`}>
                <span>{table.tableCode}</span>
              </div>
              <div className="qr-table-content">
                <div className="admin-panel-heading">
                  <div>
                    <span className="panel-kicker">{table.zone}</span>
                    <h3>Bàn {table.tableCode}</h3>
                  </div>
                  <span className={`admin-status admin-status-${table.status.toLowerCase()}`}>
                    {statusLabels[table.status]}
                  </span>
                </div>
                <dl className="qr-meta">
                  <div>
                    <dt>Số ghế</dt>
                    <dd>{table.seats}</dd>
                  </div>
                  <div>
                    <dt>Đơn hiện tại</dt>
                    <dd>{table.currentOrder ?? "Chưa có"}</dd>
                  </div>
                </dl>
                <code>{tableLink}</code>
                <div className="admin-action-row">
                  <a className="button primary" href={`/table/${table.tableCode}`} target="_blank">
                    Mở link bàn
                  </a>
                  <button className="button" type="button" onClick={() => handleCopy(table.tableCode)}>
                    {copiedTable === table.tableCode ? "Đã sao chép" : "Sao chép link"}
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}
