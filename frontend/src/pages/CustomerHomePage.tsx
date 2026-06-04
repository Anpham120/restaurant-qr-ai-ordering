import { Link } from "react-router-dom";
import { PageShell } from "./PageShell";

export function CustomerHomePage() {
  return (
    <PageShell
      eyebrow="Customer"
      title="Welcome and table entry"
      description="Landing shell for guests who arrive from QR codes or choose to browse the menu directly."
    >
      <div className="action-row">
        <Link className="button primary" to="/table/TABLE-01">
          Open table flow
        </Link>
        <Link className="button" to="/menu">
          Browse menu
        </Link>
      </div>
    </PageShell>
  );
}
