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
  Customer: "/",
};

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

  const helperText = useMemo(() => {
    if (!requestedPath) {
      return "Đăng nhập bằng tài khoản vận hành được cấp cho quản trị viên, nhân viên hoặc bếp.";
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

    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail || !password.trim()) {
      setError("Vui lòng nhập email và mật khẩu.");
      return;
    }

    setIsSubmitting(true);

    try {
      const loggedInUser = await login({ email: normalizedEmail, password });
      navigate(getRedirectPath(loggedInUser.role, requestedPath), { replace: true });
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.code === "INVALID_CREDENTIALS") {
        setError("Email hoặc mật khẩu không đúng.");
      } else {
        setError("Không đăng nhập được. Vui lòng kiểm tra kết nối backend hoặc thử lại.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title="Đăng nhập vận hành"
      description="Cổng đăng nhập dành cho quản trị viên, nhân viên phục vụ và bếp."
      variant="auth"
    >
      <div className="login-premium-layout login-premium-layout-centered">
        <section className="login-form-section">
          <form className="login-card login-card-glass" onSubmit={handleSubmit}>
            <div className="login-form-header">
              <span className="panel-kicker">CMC Operations</span>
              <h3>Đăng nhập hệ thống</h3>
            </div>

            <p className="auth-helper">{helperText}</p>

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
            <Link to="/" className="login-back-link">
              Quay lại trang quét QR
            </Link>
          </form>
        </section>
      </div>
    </PageShell>
  );
}
