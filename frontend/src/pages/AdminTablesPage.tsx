import { AdminQrTableManager } from "../components/qr/AdminQrTableManager";
import { PageShell } from "./PageShell";

export function AdminTablesPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Bàn và mã QR"
      description="Quản lý bàn CMC, liên kết QR theo mã bàn và trạng thái phục vụ trong khu vực nhà hàng."
      variant="admin"
    >
      <AdminQrTableManager />
    </PageShell>
  );
}
