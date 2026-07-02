import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Link,
  NavLink,
  Outlet,
  RouterProvider,
  createBrowserRouter,
  useLocation,
} from "react-router-dom";
import { NotFoundPage, PageTransition } from "@cmc/shared-ui";
import "@cmc/shared-ui/styles.css";
import "../../../src/styles.css";
import logoUrl from "../../../src/mocks/images/logo.png";
import { CustomerHomePage } from "../../../src/pages/CustomerHomePage";
import { TableEntryPage } from "../../../src/pages/TableEntryPage";
import { CartPage } from "../../../src/pages/CartPage";
import { OrderStatusPage } from "../../../src/pages/OrderStatusPage";

function CustomerLayout() {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const isLanding = location.pathname === "/";

  useEffect(() => setMenuOpen(false), [location.pathname, location.hash]);

  return (
    <div className={`customer-app-shell${isLanding ? " landing-shell" : ""}`}>
      <a className="skip-link" href="#main-content">
        Chuyển đến nội dung chính
      </a>
      <header className="customer-topbar">
        <Link className="customer-brand" to="/" aria-label="CMC Restaurant - Trang chủ">
          <img className="customer-brand-logo" alt="" src={logoUrl} width="54" height="54" />
          <span translate="no">
            <strong>CMC Restaurant</strong>
            <small>QR Ordering</small>
          </span>
        </Link>
        <button
          className="customer-menu-toggle"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="customer-navigation"
          aria-label={menuOpen ? "Đóng menu" : "Mở menu"}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>
        <nav
          className={`customer-nav${menuOpen ? " open" : ""}`}
          id="customer-navigation"
          aria-label="Điều hướng khách hàng"
        >
          <NavLink to="/">Trang chủ</NavLink>
          {!isLanding ? <NavLink to="/cart">Giỏ hàng</NavLink> : null}
        </nav>
      </header>
      <main className="customer-content" id="main-content">
        <PageTransition transitionKey={location.pathname}>
          <Outlet />
        </PageTransition>
      </main>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <CustomerLayout />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <CustomerHomePage /> },
      { path: "table/:tableCode", element: <TableEntryPage /> },
      { path: "cart", element: <CartPage /> },
      { path: "orders/:orderCode", element: <OrderStatusPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
