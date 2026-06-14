import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@cmc/api-client";
import { useAuth } from "@cmc/auth";
import type { UserRole } from "@cmc/shared-types";
import { PageShell } from "./PageShell";

type LoginLocationState = {
  from?: string;
};

const roleHome: Record<UserRole, string> = {
  Admin: "/admin",
  Staff: "/staff/orders",
  Kitchen: "/kitchen",
  Customer: "/menu",
};

const quickLoginAccounts: Array<{
  role: UserRole;
  email: string;
  password: string;
  icon: string;
  label: string;
  description: string;
  color: string;
}> = [
  {
    role: "Admin",
    email: "admin@restaurant.local",
    password: "Admin@123",
    icon: "👑",
    label: "Quản trị viên",
    description: "Toàn quyền hệ thống: menu, đơn, bàn, người dùng",
    color: "var(--role-admin)",
  },
  {
    role: "Staff",
    email: "staff@restaurant.local",
    password: "Staff@123",
    icon: "🧑‍💼",
    label: "Nhân viên",
    description: "Phục vụ đơn, thu ngân, xác nhận thanh toán",
    color: "var(--role-staff)",
  },
  {
    role: "Kitchen",
    email: "kitchen@restaurant.local",
    password: "Kitchen@123",
    icon: "👨‍🍳",
    label: "Đầu bếp",
    description: "Nhận món, chế biến, cập nhật trạng thái bếp",
    color: "var(--role-kitchen)",
  },
];

function canOpenPath(role: UserRole, path: string) {
  if (path.startsWith("/admin/orders")) {
    return role === "Admin" || role === "Staff";
  }
  if (path.startsWith("/admin")) {
    return role === "Admin";
  }
  if (path.startsWith("/staff")) {
    return role === "Admin" || role === "Staff";
  }
  if (path.startsWith("/kitchen")) {
    return role === "Admin" || role === "Kitchen";
  }
  return true;
}

function getRedirectPath(role: UserRole, requestedPath?: string) {
  if (requestedPath && canOpenPath(role, requestedPath)) {
    return requestedPath;
  }
  return roleHome[role];
}

export function LoginPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LoginLocationState | null;
  const requestedPath = state?.from;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeQuickLogin, setActiveQuickLogin] = useState<string | null>(null);

  const targetLabel = useMemo(() => {
    if (!requestedPath) {
      return "Chọn vai trò bên dưới để đăng nhập nhanh, hoặc nhập thông tin tài khoản.";
    }
    return `Bạn cần đăng nhập để tiếp tục tới ${requestedPath}.`;
  }, [requestedPath]);

  useEffect(() => {
    if (!loading && user) {
      navigate(getRedirectPath(user.role, requestedPath), { replace: true });
    }
  }, [loading, navigate, requestedPath, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !password.trim()) {
      setError("Vui lòng nhập email và mật khẩu.");
      return;
    }

    setIsSubmitting(true);

    try {
      const loggedInUser = await login({ email: email.trim(), password });
      navigate(getRedirectPath(loggedInUser.role, requestedPath), { replace: true });
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.code === "INVALID_CREDENTIALS") {
        setError("Email hoặc mật khẩu không đúng.");
      } else {
        setError("Không đăng nhập được. Vui lòng kiểm tra backend hoặc thử lại.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleQuickLogin(account: (typeof quickLoginAccounts)[number]) {
    setError(null);
    setActiveQuickLogin(account.role);

    try {
      const loggedInUser = await login({ email: account.email, password: account.password });
      navigate(getRedirectPath(loggedInUser.role, requestedPath), { replace: true });
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.code === "INVALID_CREDENTIALS") {
        setError(`Tài khoản ${account.role} mặc định không khớp. Kiểm tra seed password.`);
      } else {
        setError("Không đăng nhập được. Kiểm tra backend.");
      }
    } finally {
      setActiveQuickLogin(null);
    }
  }

  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title="Đăng nhập vận hành"
      description="Cổng vào dành cho admin, nhân viên phục vụ và bếp trong hệ thống CMC."
      variant="auth"
    >
      <div className="login-premium-layout">
        <section className="login-quick-section">
          <span className="panel-kicker">Đăng nhập nhanh</span>
          <h3>Chọn vai trò</h3>
          <p>Dành cho môi trường phát triển — nhấn để đăng nhập tự động.</p>

          <div className="quick-login-cards">
            {quickLoginAccounts.map((account) => (
              <button
                className={`quick-login-card ${activeQuickLogin === account.role ? "is-loading" : ""}`}
                key={account.role}
                type="button"
                onClick={() => handleQuickLogin(account)}
                disabled={isSubmitting || loading || activeQuickLogin !== null}
                style={{ "--role-accent": account.color } as React.CSSProperties}
              >
                <span className="quick-login-icon">{account.icon}</span>
                <div className="quick-login-info">
                  <strong>{account.label}</strong>
                  <small>{account.description}</small>
                </div>
                <span className={`quick-login-role-badge role-${account.role.toLowerCase()}`}>
                  {account.role}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="login-form-section">
          <form className="login-card login-card-glass" onSubmit={handleSubmit}>
            <div className="login-form-header">
              <span className="panel-kicker">Đăng nhập thủ công</span>
              <h3>Nhập tài khoản</h3>
            </div>

            <p className="auth-helper">{targetLabel}</p>

            <label>
              Email
              <input
                autoComplete="email"
                inputMode="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="email@restaurant.local"
                type="email"
                value={email}
              />
            </label>
            <label>
              Mật khẩu
              <input
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Nhập mật khẩu"
                type="password"
                value={password}
              />
            </label>
            {error ? (
              <p className="auth-error" role="alert">
                {error}
              </p>
            ) : null}
            <button className="button primary" disabled={isSubmitting || loading} type="submit">
              {isSubmitting ? "Đang đăng nhập..." : "Đăng nhập"}
            </button>
            <Link to="/menu" className="login-back-link">Quay lại thực đơn khách hàng</Link>
          </form>
        </section>
      </div>
    </PageShell>
  );
}
