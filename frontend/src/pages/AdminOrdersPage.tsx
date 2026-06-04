import { PageShell } from "./PageShell";

export function AdminOrdersPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Order management shell"
      description="Placeholder for monitoring all customer orders and resolving operational issues."
      variant="admin"
      stats={[
        { label: "Placed", value: "2", detail: "Contract status" },
        { label: "Preparing", value: "1", detail: "Contract status" },
        { label: "Ready", value: "1", detail: "Contract status" },
      ]}
    >
      <div className="kanban-grid">
        {["Placed", "Preparing", "Ready"].map((status) => (
          <section className="kanban-column" key={status}>
            <h3>{status}</h3>
            <article className="ticket-card">
              <strong>Table T-05</strong>
              <p>Order shell using contract-aligned status text.</p>
            </article>
          </section>
        ))}
      </div>
    </PageShell>
  );
}
