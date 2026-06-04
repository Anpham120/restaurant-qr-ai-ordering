import { PageShell } from "./PageShell";

export function AdminTablesPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="QR table management shell"
      description="Placeholder for table records, QR generation, and active table status."
      variant="admin"
      stats={[
        { label: "Tables", value: "12", detail: "QR records shell" },
        { label: "Occupied", value: "7", detail: "Static preview" },
      ]}
    >
      <div className="table-grid">
        {["T-01", "T-02", "T-03", "T-04", "T-05", "T-06"].map((table) => (
          <article className="table-tile" key={table}>
            <span>{table}</span>
            <strong>QR ready</strong>
          </article>
        ))}
      </div>
    </PageShell>
  );
}
