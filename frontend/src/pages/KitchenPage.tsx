import { PageShell } from "./PageShell";

export function KitchenPage() {
  return (
    <PageShell
      eyebrow="Kitchen"
      title="Bảng bếp CMC"
      description="Hàng đợi chế biến cho bếp, giữ trạng thái món rõ ràng và dễ đọc trong giờ cao điểm."
      variant="kitchen"
      stats={[
        { label: "Đang chế biến", value: "6", detail: "Theo dõi theo lane" },
        { label: "Sẵn sàng", value: "2", detail: "Chờ nhân viên phục vụ" },
      ]}
    >
      <div className="kitchen-board">
        {["Pending", "Preparing", "Ready"].map((status) => (
          <section className="kitchen-lane" key={status}>
            <h3>{status}</h3>
            <article className="kitchen-ticket">
              <strong>Bò lúc lắc x2</strong>
              <p>Table T-05</p>
            </article>
            <article className="kitchen-ticket">
              <strong>Gỏi cuốn tôm thịt x1</strong>
              <p>Table T-07</p>
            </article>
          </section>
        ))}
      </div>
    </PageShell>
  );
}
