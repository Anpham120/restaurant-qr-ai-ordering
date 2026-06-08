import { AdminQrTableManager } from "../components/qr/AdminQrTableManager";
import { PageShell } from "./PageShell";

export function AdminTablesPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Bàn và mã QR"
      description="Quản lý bàn CMC, liên kết QR theo route /table/:tableCode và trạng thái bàn phục vụ trong khu vực nhà hàng."
      variant="admin"
      stats={[
        { label: "Tổng số bàn", value: "12", detail: "Sẵn sàng tạo QR" },
        { label: "Đang phục vụ", value: "7", detail: "Dữ liệu mẫu trong ca" },
        { label: "Route QR", value: "/table/:tableCode", detail: "Đúng contract QR" },
      ]}
    >
      <AdminQrTableManager />
    </PageShell>
  );
}
