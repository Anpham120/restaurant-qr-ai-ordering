import { useParams } from "react-router-dom";
import { PageShell } from "./PageShell";

export function TableEntryPage() {
  const { tableCode } = useParams();

  return (
    <PageShell
      eyebrow="QR Flow"
      title={`Table ${tableCode ?? "unknown"}`}
      description="Placeholder for validating a QR table code before showing the order menu."
      stats={[
        { label: "Route", value: "/table/:tableCode", detail: "QR entry point" },
        { label: "Next", value: "Menu", detail: "Customer chooses dishes" },
      ]}
    >
      <div className="qr-card">
        <div className="qr-preview" aria-hidden="true">
          <span>{tableCode?.slice(-2) ?? "QR"}</span>
        </div>
        <div>
          <h3>Table session shell</h3>
          <p>
            Later this screen will confirm the table code against `GET /api/tables/{tableCode}`.
          </p>
        </div>
      </div>
    </PageShell>
  );
}
