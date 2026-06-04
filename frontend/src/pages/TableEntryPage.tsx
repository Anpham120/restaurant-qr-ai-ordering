import { useParams } from "react-router-dom";
import { PageShell } from "./PageShell";

export function TableEntryPage() {
  const { tableCode } = useParams();

  return (
    <PageShell
      eyebrow="QR Flow"
      title={`Table ${tableCode ?? "unknown"}`}
      description="Placeholder for validating a QR table code before showing the order menu."
    />
  );
}

