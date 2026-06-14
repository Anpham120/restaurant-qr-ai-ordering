import type { ReactNode } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { getStoredUser, hasAllowedRole, type UserRole } from "../../services/authService";

type ProtectedRouteProps = {
  roles: UserRole[];
  children: ReactNode;
};

export function ProtectedRoute({ roles, children }: ProtectedRouteProps) {
  const location = useLocation();
  const user = getStoredUser();

  if (!user) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  }

  if (!hasAllowedRole(user, roles)) {
    return (
      <section className="auth-blocked">
        <p className="eyebrow">Role guard</p>
        <h2>Không có quyền truy cập</h2>
        <p>
          Tài khoản hiện tại là <strong>{user.role}</strong>. Màn hình này chỉ dành cho{" "}
          <strong>{roles.join(", ")}</strong>.
        </p>
        <Link className="button primary" to="/login">
          Đăng nhập bằng tài khoản khác
        </Link>
      </section>
    );
  }

  return <>{children}</>;
}
