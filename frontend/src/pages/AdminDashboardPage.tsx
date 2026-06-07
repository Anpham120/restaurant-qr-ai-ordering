import { PageShell } from "./PageShell";

export function AdminDashboardPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Tổng quan CMC"
      description="Bảng điều khiển theo dõi đơn đang phục vụ, bàn có khách và chỉ số vận hành trong ngày."
      variant="admin"
      stats={[
        { label: "Đơn đang xử lý", value: "4", detail: "Cần theo dõi trong ca" },
        { label: "Bàn có khách", value: "7 / 12", detail: "Trạng thái bàn hiện tại" },
        { label: "Giá trị TB", value: "385.000đ", detail: "Dữ liệu mẫu vận hành" },
      ]}
    >
      <div className="table-shell">
        <div className="table-row table-head">
          <span>Đơn</span>
          <span>Bàn</span>
          <span>Trạng thái</span>
          <span>Tổng tiền</span>
        </div>
        {[
          ["ORD-001", "T-05", "Preparing", "495.000đ"],
          ["ORD-002", "T-07", "Placed", "250.000đ"],
          ["ORD-003", "T-01", "Ready", "670.000đ"],
        ].map(([order, table, status, total]) => (
          <div className="table-row" key={order}>
            <strong>{order}</strong>
            <span>{table}</span>
            <span className={`mini-badge ${status.toLowerCase()}`}>{status}</span>
            <strong>{total}</strong>
          </div>
        ))}
      </div>
    </PageShell>
  );
}
