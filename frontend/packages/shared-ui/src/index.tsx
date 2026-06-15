import { useState, type FormEvent, type ReactNode } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@cmc/auth";
import type { UserRole } from "@cmc/shared-types";

export function Button({
  children,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  return (
    <button className={`cmc-button cmc-button--${variant}`} {...props}>
      {children}
    </button>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`cmc-card ${className}`}>{children}</section>;
}

export function StatePanel({
  title,
  message,
  kind = "empty",
}: {
  title: string;
  message: string;
  kind?: "empty" | "loading" | "error";
}) {
  return (
    <div className={`cmc-state cmc-state--${kind}`} role={kind === "error" ? "alert" : "status"}>
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}

export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
}) {
  return <span className={`cmc-badge cmc-badge--${tone}`}>{children}</span>;
}

export function NotFoundPage() {
  return (
    <StatePanel
      title="Không tìm thấy trang"
      message="Đường dẫn này không tồn tại trong portal hiện tại."
      kind="error"
    />
  );
}

export function UnauthorizedPage() {
  return (
    <StatePanel
      title="Không có quyền truy cập"
      message="Tài khoản của bạn không có vai trò phù hợp với portal này."
      kind="error"
    />
  );
}

export type PortalLink = { to: string; label: string };

export function OperationsLayout({
  title,
  subtitle,
  links,
}: {
  title: string;
  subtitle: string;
  links: PortalLink[];
}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="cmc-operations-shell">
      <aside className="cmc-sidebar">
        <div className="cmc-brand">
          <span className="cmc-brand-mark">CMC</span>
          <div>
            <strong>{title}</strong>
            <small>{subtitle}</small>
          </div>
        </div>
        <nav aria-label={`${title} navigation`}>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/" || link.to.split("/").length === 2}
              className={({ isActive }) => (isActive ? "cmc-nav-link is-active" : "cmc-nav-link")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="cmc-user">
          <span>{user?.fullName}</span>
          <small>{user?.role}</small>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Đăng xuất
          </button>
        </div>
      </aside>
      <main className="cmc-portal-content">
        <Outlet />
      </main>
    </div>
  );
}

export function LoginPage({
  portalName,
  allowedRoles,
  roleRedirects = {},
}: {
  portalName: string;
  allowedRoles: UserRole[];
  roleRedirects?: Partial<Record<UserRole, string>>;
}) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const target = (location.state as { from?: string } | null)?.from ?? "/";

  function resolveTarget(role: UserRole) {
    if (target !== "/") {
      return target;
    }
    return roleRedirects[role] ?? target;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await login({ email, password });
      if (!allowedRoles.includes(user.role)) {
        setError(`Tài khoản ${user.role} không được truy cập ${portalName}.`);
        return;
      }
      navigate(resolveTarget(user.role), { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Đăng nhập thất bại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="cmc-login-shell">
      <div className="cmc-login-premium">
        <section className="cmc-form-section">
          <Card className="cmc-login-card">
            <p className="cmc-eyebrow">{portalName}</p>
            <h2>Đăng nhập hệ thống</h2>
            <p>Nhập email và mật khẩu tài khoản vận hành.</p>
            <form onSubmit={submit}>
              <label>
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="username"
                  placeholder="email@restaurant.local"
                />
              </label>
              <label>
                Mật khẩu
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="Nhập mật khẩu"
                />
              </label>
              {error ? (
                <p className="cmc-form-error" role="alert">
                  {error}
                </p>
              ) : null}
              <Button disabled={busy} type="submit">
                {busy ? "Đang đăng nhập..." : "Đăng nhập"}
              </Button>
            </form>
          </Card>
        </section>
      </div>
    </main>
  );
}
