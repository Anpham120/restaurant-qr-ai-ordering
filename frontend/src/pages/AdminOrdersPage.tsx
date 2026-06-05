import { PageShell } from "./PageShell";

export function AdminOrdersPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Quản lý đơn hàng"
      description="Theo dõi đơn mới, tiến độ bếp và các đơn cần nhân viên xử lý trong ca."
      variant="admin"
      stats={[
        { label: "Mới đặt", value: "2", detail: "Chờ xác nhận" },
        { label: "Đang làm", value: "1", detail: "Bếp đang xử lý" },
        { label: "Sẵn sàng", value: "1", detail: "Chờ phục vụ" },
      ]}
    >
      <div className="kanban-grid">
        {["Placed", "Preparing", "Ready"].map((status) => (
          <section className="kanban-column" key={status}>
            <h3>{status}</h3>
            <article className="ticket-card">
              <strong>Table T-05</strong>
              <p>Đơn mẫu dùng đúng status contract để sẵn sàng nối API.</p>
            </article>
          </section>
        ))}
      </div>
    </PageShell>
  );
}
