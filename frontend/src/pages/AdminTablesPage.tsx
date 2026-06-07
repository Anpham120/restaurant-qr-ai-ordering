import { PageShell } from "./PageShell";

export function AdminTablesPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Bàn và mã QR"
      description="Quản lý bàn CMC, liên kết QR và trạng thái bàn phục vụ trong khu vực nhà hàng."
      variant="admin"
      stats={[
        { label: "Tổng số bàn", value: "12", detail: "Sẵn sàng tạo QR" },
        { label: "Đang phục vụ", value: "7", detail: "Dữ liệu mẫu trong ca" },
      ]}
    >
      <div className="table-grid">
        {["T-01", "T-02", "T-03", "T-04", "T-05", "T-06"].map((table) => (
          <article className="table-tile" key={table}>
            <span>{table}</span>
            <strong>QR sẵn sàng</strong>
          </article>
        ))}
      </div>
    </PageShell>
  );
}
