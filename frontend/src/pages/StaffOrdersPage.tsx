import { PageShell } from "./PageShell";

export function StaffOrdersPage() {
  return (
    <PageShell
      eyebrow="Staff"
      title="Service orders shell"
      description="Placeholder for staff order triage, customer notes, and service status updates."
      variant="staff"
      stats={[
        { label: "Pending items", value: "5", detail: "Item status shell" },
        { label: "Ready items", value: "3", detail: "Pickup preview" },
      ]}
    >
      <div className="kanban-grid">
        {["Pending", "Preparing", "Ready"].map((status) => (
          <section className="kanban-column" key={status}>
            <h3>{status}</h3>
            <article className="ticket-card">
              <strong>Table T-07</strong>
              <p>Staff service card placeholder.</p>
            </article>
          </section>
        ))}
      </div>
    </PageShell>
  );
}
