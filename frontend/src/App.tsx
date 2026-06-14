import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@cmc/auth";
import type { UserRole } from "@cmc/shared-types";
import logoUrl from "./mocks/images/logo.png";
import { CustomerAiLauncher } from "./components/customer/CustomerAiLauncher";

const customerLinks = [
  { to: "/menu", text: "Thực đơn" },
  { to: "/menu", text: "Ưu đãi" },
  { to: "/orders/ORD-1001", text: "Theo dõi đơn" },
  { to: "/chat", text: "Hỏi AI" },
];

const operationsLinks: Array<{ to: string; text: string; roles?: UserRole[] }> = [
  { to: "/login", text: "Đăng nhập" },
  { to: "/admin", text: "Tổng quan", roles: ["Admin"] },
  { to: "/admin/menu", text: "Thực đơn", roles: ["Admin"] },
  { to: "/admin/categories", text: "Danh mục", roles: ["Admin"] },
  { to: "/admin/orders", text: "Đơn hàng", roles: ["Admin", "Staff"] },
  { to: "/admin/tables", text: "Bàn & QR", roles: ["Admin"] },
  { to: "/admin/users", text: "Người dùng", roles: ["Admin"] },
  { to: "/staff/orders", text: "Nhân viên", roles: ["Admin", "Staff"] },
  { to: "/kitchen", text: "Bếp", roles: ["Admin", "Kitchen"] },
];

export default function App() {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const isOperationsRoute =
    pathname.startsWith("/admin") ||
    pathname.startsWith("/staff") ||
    pathname.startsWith("/kitchen") ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/unauthorized");

  const visibleOperationsLinks = operationsLinks.filter((link) => {
    if (!link.roles) {
      return !user;
    }
    return user ? link.roles.includes(user.role) : false;
  });

  if (!isOperationsRoute) {
    return (
      <div className="customer-app-shell">
        <header className="customer-topbar">
          <NavLink className="customer-brand" to="/">
            <img className="customer-brand-logo" alt="CMC Restaurant" src={logoUrl} />
            <span>
              <strong>CMC Restaurant</strong>
              <small>QR AI Ordering</small>
            </span>
          </NavLink>
          <nav className="customer-nav" aria-label="Customer navigation">
            {customerLinks.map((link) => (
              <NavLink
                end={link.to === "/"}
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  isActive ? "customer-nav-link active" : "customer-nav-link"
                }
              >
                {link.text}
              </NavLink>
            ))}
          </nav>
          <NavLink className="customer-login-link" to="/login">
            Đăng nhập staff
          </NavLink>
        </header>
        <main className="customer-content">
          <Outlet />
        </main>
        <CustomerAiLauncher />
      </div>
    );
  }

  return (
    <div className="app-shell operations-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <img className="brand-logo" alt="CMC Restaurant" src={logoUrl} />
          <p className="eyebrow">Restaurant</p>
          <h1>Operations</h1>
        </div>
        <nav className="nav-groups">
          <section className="nav-group">
            <h2>CMC Control</h2>
            <div className="nav-links">
              {visibleOperationsLinks.map((link) => (
                <NavLink
                  end={link.to === "/"}
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    isActive ? "nav-link active" : "nav-link"
                  }
                >
                  {link.text}
                </NavLink>
              ))}
            </div>
          </section>
        </nav>
        {user ? (
          <section className="auth-sidebar-card" aria-label="Phiên đăng nhập">
            <span>{user.role}</span>
            <strong>{user.fullName}</strong>
            <small>{user.email}</small>
            <button type="button" onClick={logout}>
              Đăng xuất
            </button>
          </section>
        ) : null}
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
