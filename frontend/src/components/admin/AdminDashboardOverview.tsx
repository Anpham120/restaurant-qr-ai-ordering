const serviceHighlights = [
  {
    label: "Luồng QR",
    value: "/table/T-05",
    detail: "Khách quét QR, vào menu và tạo đơn tại bàn.",
  },
  {
    label: "Điều phối đơn",
    value: "Admin -> Staff -> Bếp",
    detail: "Mỗi vai trò nhìn đúng trạng thái cần xử lý trong ca.",
  },
  {
    label: "Realtime demo",
    value: "Mock event",
    detail: "Bảng bếp phát event để minh họa cập nhật không cần reload.",
  },
];

const activeOrders = [
  { code: "ORDER-001", table: "T-05", status: "Preparing", total: "310.000đ" },
  { code: "ORDER-002", table: "Pickup", status: "Ready", total: "430.000đ" },
  { code: "ORDER-003", table: "Delivery", status: "Delivered", total: "565.000đ" },
];

const shiftChecklist = [
  "Kiểm tra QR của từng bàn trước giờ mở ca.",
  "Xác nhận đơn mới trong 2 phút đầu.",
  "Đẩy món Ready sang staff để tránh nguội món.",
  "Đối soát COD/Paid cuối ca trước khi xuất báo cáo.",
];

export function AdminDashboardOverview() {
  return (
    <div className="ops-dashboard-grid">
      <section className="ops-hero-panel">
        <span className="panel-kicker">Ca vận hành hôm nay</span>
        <h3>Nhà hàng đang hoạt động ổn định</h3>
        <p>
          Màn tổng quan này gom nhanh trạng thái đơn, QR, bếp và staff để demo cuối kỳ có
          đủ câu chuyện vận hành phía nhà hàng.
        </p>
        <div className="ops-health-row">
          <span>Menu online</span>
          <span>Bếp sẵn sàng</span>
          <span>QR hợp lệ</span>
        </div>
      </section>

      <section className="ops-panel">
        <div className="admin-panel-heading">
          <div>
            <span className="panel-kicker">Đơn nổi bật</span>
            <h3>Ưu tiên trong ca</h3>
          </div>
          <span className="admin-status admin-status-ready">Live demo</span>
        </div>
        <div className="table-shell ops-order-table">
          <div className="table-row table-head">
            <span>Đơn</span>
            <span>Bàn/Kênh</span>
            <span>Trạng thái</span>
            <span>Tổng</span>
          </div>
          {activeOrders.map((order) => (
            <div className="table-row" key={order.code}>
              <strong>{order.code}</strong>
              <span>{order.table}</span>
              <span className={`mini-badge ${order.status.toLowerCase()}`}>
                {order.status}
              </span>
              <strong>{order.total}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="ops-panel">
        <div className="admin-panel-heading">
          <div>
            <span className="panel-kicker">Điểm demo</span>
            <h3>Luồng cần trình bày</h3>
          </div>
        </div>
        <div className="ops-feature-list">
          {serviceHighlights.map((item) => (
            <article className="ops-feature-card" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="ops-panel">
        <div className="admin-panel-heading">
          <div>
            <span className="panel-kicker">Checklist</span>
            <h3>Trước khi quay báo cáo</h3>
          </div>
        </div>
        <ol className="ops-checklist">
          {shiftChecklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      </section>
    </div>
  );
}
