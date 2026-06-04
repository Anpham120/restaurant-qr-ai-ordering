import { PageShell } from "./PageShell";

export function KitchenPage() {
  return (
    <PageShell
      eyebrow="Kitchen"
      title="Kitchen board shell"
      description="Placeholder for realtime kitchen item queues and preparation status changes."
      variant="kitchen"
      stats={[
        { label: "Preparing", value: "6", detail: "Kitchen queue shell" },
        { label: "Ready", value: "2", detail: "Future SignalR events" },
      ]}
    >
      <div className="kitchen-board">
        {["Pending", "Preparing", "Ready"].map((status) => (
          <section className="kitchen-lane" key={status}>
            <h3>{status}</h3>
            <article className="kitchen-ticket">
              <strong>Bruschetta x2</strong>
              <p>Table T-05</p>
            </article>
            <article className="kitchen-ticket">
              <strong>Soup of the Day x1</strong>
              <p>Table T-07</p>
            </article>
          </section>
        ))}
      </div>
    </PageShell>
  );
}
