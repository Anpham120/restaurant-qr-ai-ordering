import { Link } from "react-router-dom";
import { PageShell } from "./PageShell";

export function CustomerHomePage() {
  return (
    <PageShell
      eyebrow="Customer"
      title="Welcome and table entry"
      description="Landing shell for guests who arrive from QR codes or choose to browse the menu directly."
      stats={[
        { label: "Flow", value: "QR first", detail: "Table code starts the order" },
        { label: "Scope", value: "Shell", detail: "No live API calls yet" },
      ]}
    >
      <div className="action-row">
        <Link className="button primary" to="/table/TABLE-01">
          Open table flow
        </Link>
        <Link className="button" to="/menu">
          Browse menu
        </Link>
      </div>
      <div className="panel-grid">
        <article className="feature-panel">
          <span className="panel-kicker">Step 1</span>
          <h3>Scan table QR</h3>
          <p>Guests land on `/table/:tableCode` before browsing the menu.</p>
        </article>
        <article className="feature-panel">
          <span className="panel-kicker">Step 2</span>
          <h3>Build cart</h3>
          <p>Menu and cart shells are ready for later API integration.</p>
        </article>
        <article className="feature-panel">
          <span className="panel-kicker">Step 3</span>
          <h3>Track order</h3>
          <p>Order status route is available for realtime updates later.</p>
        </article>
      </div>
    </PageShell>
  );
}
