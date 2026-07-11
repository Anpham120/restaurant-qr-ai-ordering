import { CustomerMenuPage } from "../pages/customer/CustomerMenuPage";
import { useOrderingSession } from "./OrderingSessionProvider";

export function OrderingMenuPage() {
  const { context } = useOrderingSession();
  return <CustomerMenuPage mode="ordering" qrToken={context.qrToken} tableCode={context.tableCode} />;
}
