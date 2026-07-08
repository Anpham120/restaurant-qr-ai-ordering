import { Link } from "react-router-dom";
import { ChefHat, Flame, ListChecks } from "lucide-react";
import "../components/operations/operations.css";

const kitchenActions = [
  {
    title: "Bảng bếp realtime",
    href: "board",
    icon: <Flame size={24} />,
    description: "Nhận đơn đã xác nhận, chuyển món sang đang nấu và báo sẵn sàng.",
    detail: "Dữ liệu lấy từ backend và cập nhật qua realtime order hub.",
  },
  {
    title: "Tình trạng món",
    href: "board?menu=1",
    icon: <ListChecks size={24} />,
    description: "Tắt/mở món đang hết trong ca để khách và nhân viên thấy đúng thực đơn.",
    detail: "Chỉ thay đổi trạng thái có sẵn, không sửa giá hoặc danh mục.",
  },
];

export function KitchenHomePage() {
  return (
    <div>
      <div className="ops-page-header">
        <h1>Nhà bếp</h1>
        <p>Portal dành cho bếp: xử lý món theo thứ tự đơn và cập nhật tình trạng món.</p>
      </div>

      <div className="ops-role-hero ops-role-hero--kitchen">
        <div>
          <span className="ops-role-kicker">Kitchen Portal</span>
          <h2>Quyền của ca bếp</h2>
          <p>
            Tài khoản Kitchen chỉ nhìn thấy pipeline chế biến và trạng thái món. Thu tiền, tạo
            tài khoản, cấu hình bàn QR và báo cáo doanh thu không xuất hiện trong portal này.
          </p>
        </div>
        <ChefHat size={48} aria-hidden="true" />
      </div>

      <div className="ops-action-grid">
        {kitchenActions.map((action) => (
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
