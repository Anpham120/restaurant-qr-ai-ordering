import { Link } from "react-router-dom";
import {
  BadgeCheck,
  ChefHat,
  ClipboardList,
  CreditCard,
  ShieldCheck,
  Users,
} from "lucide-react";
import "../../components/operations/operations.css";

const roleCards = [
  {
    role: "Admin",
    title: "Quản trị viên",
    portal: "Admin Portal",
    href: "/",
    badge: "Toàn quyền",
    icon: <ShieldCheck size={22} />,
    summary: "Quản lý cấu hình nhà hàng, tài khoản vận hành, thực đơn, phiên bàn và báo cáo.",
    permissions: [
      "Tạo tài khoản Staff, Kitchen, Admin",
      "Quản lý thực đơn, danh mục, bàn và mã QR",
      "Theo dõi đơn hàng, hóa đơn, phiên bàn, khuyến mãi và báo cáo",
    ],
    denied: ["Không dùng để khách đặt món trực tiếp"],
  },
  {
    role: "Staff",
    title: "Lễ tân / phục vụ",
    portal: "Staff Portal",
    href: "/staff",
    badge: "Vận hành sảnh",
    icon: <Users size={22} />,
    summary: "Tiếp nhận đơn tại bàn, điều phối phục vụ, xác nhận thu tiền và hoàn tất đơn.",
    permissions: [
      "Xác nhận hoặc hủy đơn mới",
      "Đánh dấu món đã phục vụ, hoàn tất đơn sau khi thu tiền",
      "Xác nhận, từ chối, hoàn tiền và mở QR thanh toán",
    ],
    denied: ["Không sửa tài khoản", "Không chỉnh cấu hình hệ thống", "Không tắt/mở món của bếp"],
  },
  {
    role: "Kitchen",
    title: "Nhà bếp",
    portal: "Kitchen Portal",
    href: "/kitchen",
    badge: "Sản xuất món",
    icon: <ChefHat size={22} />,
    summary: "Nhận đơn đã xác nhận, cập nhật tiến độ món và báo món sẵn sàng theo thời gian thực.",
    permissions: [
      "Xem đơn Confirmed, Preparing, Ready",
      "Chuyển món từ chờ nấu sang đang nấu, rồi sẵn sàng",
      "Tắt/mở trạng thái có sẵn của món trong ca làm",
    ],
    denied: ["Không thu tiền", "Không tạo tài khoản", "Không quản lý bàn hoặc QR"],
  },
];

export function RoleAccessPage() {
  return (
    <div>
      <div className="ops-page-header">
        <h1>Phân quyền vận hành</h1>
        <p>Mỗi tài khoản chỉ nhìn thấy đúng portal và thao tác nghiệp vụ của vai trò được cấp.</p>
      </div>

      <div className="ops-role-grid">
        {roleCards.map((card) => (
          <article className={`ops-role-card ops-role-card--${card.role.toLowerCase()}`} key={card.role}>
            <header className="ops-role-card-header">
              <span className="ops-role-icon" aria-hidden="true">
                {card.icon}
              </span>
              <div>
                <span className="ops-role-kicker">{card.portal}</span>
                <h2>{card.title}</h2>
              </div>
              <span className="ops-role-badge">{card.badge}</span>
            </header>

            <p className="ops-role-summary">{card.summary}</p>

            <div className="ops-permission-columns">
              <section>
                <h3>Được phép</h3>
                <ul>
                  {card.permissions.map((item) => (
                    <li key={item}>
                      <BadgeCheck size={15} />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </section>
              <section>
                <h3>Không làm</h3>
                <ul>
                  {card.denied.map((item) => (
                    <li key={item} className="is-muted">
                      <span aria-hidden="true">-</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </section>
            </div>

            <Link className="ops-btn ops-btn--primary ops-role-link" to={card.href}>
              Mở {card.portal}
            </Link>
          </article>
        ))}
      </div>

      <div className="ops-flow-strip">
        <div>
          <ClipboardList size={20} />
          <strong>Staff nhận đơn</strong>
          <span>{"Placed -> Confirmed"}</span>
        </div>
        <div>
          <ChefHat size={20} />
          <strong>Bếp chế biến</strong>
          <span>{"Confirmed -> Preparing -> Ready"}</span>
        </div>
        <div>
          <CreditCard size={20} />
          <strong>Staff thu tiền</strong>
          <span>{"Served -> Completed"}</span>
        </div>
      </div>
    </div>
  );
}
