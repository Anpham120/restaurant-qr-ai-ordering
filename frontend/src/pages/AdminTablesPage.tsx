import { AdminQrTableManager } from "../components/qr/AdminQrTableManager";
import { PageShell } from "./PageShell";

export function AdminTablesPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Bàn và mã QR"
      description="Quản lý link QR theo bàn. Link được tạo cho customer portal để khách mở đúng phiên bàn trước khi đặt món."
      variant="admin"
    >
      <AdminQrTableManager />
    </PageShell>
  );
}
