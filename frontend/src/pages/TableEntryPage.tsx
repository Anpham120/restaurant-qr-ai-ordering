import { useParams } from "react-router-dom";
import { CustomerMenuPage } from "./customer/CustomerMenuPage";

export function TableEntryPage() {
  const { tableCode } = useParams();

  return <CustomerMenuPage tableCode={tableCode} />;
}
