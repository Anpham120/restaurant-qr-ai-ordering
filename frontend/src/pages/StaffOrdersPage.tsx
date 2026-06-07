import { PageShell } from "./PageShell";

export function StaffOrdersPage() {
  return (
    <PageShell
      eyebrow="Staff"
      title="Đơn cần phục vụ"
      description="Bảng theo dõi để nhân viên CMC xác nhận, phục vụ món và cập nhật trạng thái bàn."
      variant="staff"
      stats={[
        { label: "Món chờ xử lý", value: "5", detail: "Cần theo dõi với bếp" },
        { label: "Món sẵn sàng", value: "3", detail: "Cần mang ra bàn" },
      ]}
    >
      <div className="kanban-grid">
        {["Pending", "Preparing", "Ready"].map((status) => (
          <section className="kanban-column" key={status}>
            <h3>{status}</h3>
            <article className="ticket-card">
              <strong>Table T-07</strong>
              <p>Theo dõi ghi chú khách và thời điểm phục vụ món.</p>
            </article>
          </section>
        ))}
      </div>
    </PageShell>
  );
}
