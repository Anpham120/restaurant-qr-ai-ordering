import { NavLink, Outlet, useLocation } from "react-router-dom";
import logoUrl from "./mocks/images/logo.png";
import { CustomerAiLauncher } from "./components/customer/CustomerAiLauncher";

const customerLinks = [
  { to: "/menu", text: "Thực đơn" },
  { to: "/menu", text: "Ưu đãi" },
  { to: "/orders/ORD-1001", text: "Theo dõi đơn" },
  { to: "/chat", text: "Hỏi AI" },
];

const operationsLinks = [
  { to: "/login", text: "Đăng nhập" },
  { to: "/admin", text: "Tổng quan" },
  { to: "/admin/menu", text: "Thực đơn" },
  { to: "/admin/orders", text: "Đơn hàng" },
  { to: "/admin/tables", text: "Bàn & QR" },
  { to: "/staff/orders", text: "Nhân viên" },
  { to: "/kitchen", text: "Bếp" },
];

export default function App() {
  const { pathname } = useLocation();
  const isOperationsRoute =
    pathname.startsWith("/admin") ||
    pathname.startsWith("/staff") ||
    pathname.startsWith("/kitchen") ||
    pathname.startsWith("/login");

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
              {operationsLinks.map((link) => (
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
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
