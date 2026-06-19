import { useParams, useSearchParams } from "react-router-dom";
import { CustomerMenuPage } from "./customer/CustomerMenuPage";

export function TableEntryPage() {
  const { tableCode } = useParams();
  const [searchParams] = useSearchParams();
  const qrToken = searchParams.get("qr") ?? undefined;

  return <CustomerMenuPage qrToken={qrToken} tableCode={tableCode} />;
}
