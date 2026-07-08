import { Link } from "react-router-dom";
import { ClipboardCheck, CreditCard, UtensilsCrossed } from "lucide-react";
import "../components/operations/operations.css";

const staffActions = [
  {
    title: "Điều phối đơn",
    href: "orders",
    icon: <ClipboardCheck size={24} />,
    description: "Xác nhận đơn mới, theo dõi món sẵn sàng và đánh dấu đã phục vụ.",
    detail: "Dùng cho lễ tân hoặc nhân viên sảnh khi nhận đơn từ QR tại bàn.",
  },
  {
    title: "Thu ngân",
    href: "payments",
    icon: <CreditCard size={24} />,
    description: "Xác nhận thu tiền, từ chối giao dịch lỗi, hoàn tiền khi cần.",
    detail: "Kết nối trực tiếp trạng thái thanh toán của đơn hàng.",
  },
];

export function StaffHomePage() {
  return (
    <div>
      <div className="ops-page-header">
        <h1>Lễ tân / phục vụ</h1>
        <p>Portal dành cho nhân viên sảnh: nhận đơn, phục vụ món và thu tiền tại bàn.</p>
      </div>

      <div className="ops-role-hero ops-role-hero--staff">
        <div>
          <span className="ops-role-kicker">Staff Portal</span>
          <h2>Quyền của ca sảnh</h2>
          <p>
            Tài khoản Staff chỉ thao tác trên đơn hàng và thanh toán. Các mục quản trị như tài
            khoản, thực đơn, bàn, QR và báo cáo được khóa cho Admin.
          </p>
        </div>
        <UtensilsCrossed size={46} aria-hidden="true" />
      </div>

      <div className="ops-action-grid">
        {staffActions.map((action) => (
          <Link className="ops-action-card" to={action.href} key={action.href}>
            <span className="ops-action-icon" aria-hidden="true">
              {action.icon}
            </span>
            <strong>{action.title}</strong>
            <p>{action.description}</p>
            <small>{action.detail}</small>
          </Link>
        ))}
      </div>
    </div>
  );
}
