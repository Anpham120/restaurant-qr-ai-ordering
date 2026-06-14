import { AdminQrTableManager } from "../components/qr/AdminQrTableManager";
import { PageShell } from "./PageShell";

export function AdminTablesPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Bàn và mã QR"
      description="Quản lý bàn CMC, liên kết QR theo mã bàn và trạng thái phục vụ trong khu vực nhà hàng."
      variant="admin"
      stats={[
        { label: "Tổng số bàn", value: "6", detail: "Đã cấu hình trong sơ đồ" },
        { label: "Đang phục vụ", value: "2", detail: "Có đơn đang hoạt động" },
        { label: "QR sẵn sàng", value: "6 / 6", detail: "Mở menu theo mã bàn" },
      ]}
    >
      <AdminQrTableManager />
    </PageShell>
  );
}
