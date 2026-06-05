import { useParams } from "react-router-dom";
import { PageShell } from "./PageShell";

export function OrderStatusPage() {
  const { orderCode } = useParams();

  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title={`Đơn ${orderCode ?? "unknown"}`}
      description="Theo dõi tiến độ đơn hàng và trạng thái từng bước phục vụ theo phong cách CMC."
      stats={[
        { label: "Trạng thái đơn", value: "Placed", detail: "Dữ liệu mẫu theo contract" },
        { label: "Bếp", value: "Preparing", detail: "Sẵn sàng nối realtime" },
      ]}
    >
      <div className="timeline">
        {["Placed", "Preparing", "Ready"].map((step, index) => (
          <div className="timeline-step" key={step}>
            <span>{index + 1}</span>
            <div>
              <h3>{step}</h3>
              <p>{index === 0 ? "Đơn đã được tiếp nhận" : "Chờ sự kiện realtime"}</p>
            </div>
          </div>
        ))}
      </div>
    </PageShell>
  );
}
