import { useParams } from "react-router-dom";
import { TableScanPage } from "../ordering/TableScanPage";

export function TableEntryPage() {
  const { tableCode } = useParams();
  return <TableScanPage tableCode={tableCode} />;
}
