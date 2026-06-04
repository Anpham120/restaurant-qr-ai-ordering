import { PageShell } from "./PageShell";

export function AdminDashboardPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Restaurant dashboard shell"
      description="Future restaurant KPIs, active orders, and management shortcuts will appear here."
      variant="admin"
      stats={[
        { label: "Active orders", value: "4", detail: "Dashboard shell" },
        { label: "Tables occupied", value: "7 / 12", detail: "Static preview" },
        { label: "Avg order", value: "$38.50", detail: "Placeholder metric" },
      ]}
    >
      <div className="table-shell">
        <div className="table-row table-head">
          <span>Order</span>
          <span>Table</span>
          <span>Status</span>
          <span>Total</span>
        </div>
        {[
          ["ORD-001", "T-05", "Preparing", "$49.50"],
          ["ORD-002", "T-07", "Placed", "$25.00"],
          ["ORD-003", "T-01", "Ready", "$67.00"],
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
