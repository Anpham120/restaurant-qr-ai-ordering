import { useParams } from "react-router-dom";
import { PageShell } from "./PageShell";

export function OrderStatusPage() {
  const { orderCode } = useParams();

  return (
    <PageShell
      eyebrow="Customer"
      title={`Order ${orderCode ?? "unknown"}`}
      description="Realtime order status and item progress updates will be connected in a later issue."
      stats={[
        { label: "Order status", value: "Placed", detail: "Contract-aligned placeholder" },
        { label: "Kitchen", value: "Preparing", detail: "Future SignalR update" },
      ]}
    >
      <div className="timeline">
        {["Placed", "Preparing", "Ready"].map((step, index) => (
          <div className="timeline-step" key={step}>
            <span>{index + 1}</span>
            <div>
              <h3>{step}</h3>
              <p>{index === 0 ? "Order accepted shell" : "Realtime event placeholder"}</p>
            </div>
          </div>
        ))}
      </div>
    </PageShell>
  );
}
