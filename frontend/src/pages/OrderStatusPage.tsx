import { useParams } from "react-router-dom";
import { PageShell } from "./PageShell";

export function OrderStatusPage() {
  const { orderCode } = useParams();

  return (
    <PageShell
      eyebrow="Customer"
      title={`Order ${orderCode ?? "unknown"}`}
      description="Realtime order status and item progress updates will be connected in a later issue."
    />
  );
}

