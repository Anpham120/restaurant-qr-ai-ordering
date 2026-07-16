import { Link } from "react-router-dom";
import { PageShell } from "./PageShell";

export function UnauthorizedPage() {
  return (
    <PageShell
      eyebrow="Phân quyền"
      title="Không đủ quyền truy cập"
      description="Tài khoản hiện tại không có vai trò phù hợp để mở màn hình này."
      variant="auth"
    >
      <div className="login-card" role="alert">
        <p>
          Vui lòng đăng nhập bằng tài khoản được cấp quyền Admin, Staff hoặc Kitchen đúng với
          màn hình cần sử dụng.
        </p>
        <Link className="button primary" to="/login">
          Đăng nhập tài khoản khác
        </Link>
      </div>
    </PageShell>
  );
}
