import { PageShell } from "./PageShell";

export function AdminMenuPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Menu management shell"
      description="Placeholder for creating, editing, hiding, and reordering menu items."
      variant="admin"
      stats={[
        { label: "Menu items", value: "18", detail: "Static management preview" },
        { label: "Unavailable", value: "2", detail: "Visibility shell" },
      ]}
    >
      <div className="panel-grid">
        {["Categories", "Availability", "Pricing"].map((item) => (
          <article className="feature-panel" key={item}>
            <span className="panel-kicker">Admin</span>
            <h3>{item}</h3>
            <p>Placeholder card for future menu operations.</p>
          </article>
        ))}
      </div>
    </PageShell>
  );
}
