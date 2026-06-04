import { NavLink, Outlet } from "react-router-dom";

const navGroups = [
  {
    label: "Customer",
    links: [
      { to: "/", text: "Home" },
      { to: "/table/TABLE-01", text: "QR Table" },
      { to: "/menu", text: "Menu" },
      { to: "/cart", text: "Cart" },
      { to: "/orders/ORDER-001", text: "Order Status" },
      { to: "/chat", text: "AI Chat" },
    ],
  },
  {
    label: "Operations",
    links: [
      { to: "/login", text: "Login" },
      { to: "/admin", text: "Admin" },
      { to: "/admin/menu", text: "Admin Menu" },
      { to: "/admin/orders", text: "Admin Orders" },
      { to: "/admin/tables", text: "QR Tables" },
      { to: "/staff/orders", text: "Staff Orders" },
      { to: "/kitchen", text: "Kitchen" },
    ],
  },
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark">QR</span>
          <p className="eyebrow">Restaurant QR</p>
          <h1>AI Ordering</h1>
        </div>
        <nav className="nav-groups">
          {navGroups.map((group) => (
            <section className="nav-group" key={group.label}>
              <h2>{group.label}</h2>
              <div className="nav-links">
                {group.links.map((link) => (
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
          ))}
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
