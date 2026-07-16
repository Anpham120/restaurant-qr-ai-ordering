import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Link,
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
import { ChatPage } from "../../../src/pages/ChatPage";
import { CustomerMenuPage } from "../../../src/pages/customer/CustomerMenuPage";
import { RestaurantAlbumPage } from "../../../src/pages/RestaurantAlbumPage";
import { CustomerFloatingCart } from "../../../src/components/customer/CustomerFloatingCart";

function CustomerLayout() {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const isLanding = location.pathname === "/";

  useEffect(() => setMenuOpen(false), [location.pathname, location.hash]);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", handler, { passive: true });
    handler();
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <div className={isLanding ? "landing-shell" : "customer-app-shell"}>
      <a className="skip-link" href="#main-content">
        Chuyển đến nội dung chính
      </a>

      {/* Glassmorphism header — always scrolled on non-landing pages */}
      <header className={`landing-header${(scrolled || !isLanding) ? " scrolled" : ""}`}>
        <div className="landing-header-inner">
          <div className="landing-header-bg" aria-hidden="true" />
          <Link className="landing-brand" to="/" aria-label="CMC Restaurant - Trang chủ">
            <img className="landing-brand-logo" alt="" src={logoUrl} width="44" height="44" />
            <span className="landing-brand-text" translate="no">
              <strong>CMC Restaurant</strong>
              <small>QR Ordering</small>
            </span>
          </Link>

          <button
            className="landing-menu-toggle"
            type="button"
            aria-expanded={menuOpen}
            aria-controls="customer-navigation"
            aria-label={menuOpen ? "Đóng menu" : "Mở menu"}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <span />
            <span />
            <span />
          </button>

          <nav
            className={`landing-nav${menuOpen ? " open" : ""}`}
            id="customer-navigation"
            aria-label="Điều hướng"
          >
            <a href={isLanding ? "#gioi-thieu" : "/#gioi-thieu"}>
              <i className="fa-solid fa-circle-info" style={{ marginRight: 6 }}></i>Giới thiệu
            </a>
            <Link to="/menu">
              <i className="fa-solid fa-utensils" style={{ marginRight: 6 }}></i>Thực đơn
            </Link>
            <a href={isLanding ? "#danh-gia" : "/#danh-gia"}>
              <i className="fa-solid fa-star" style={{ marginRight: 6 }}></i>Đánh giá
            </a>
            <Link to="/album">
              <i className="fa-solid fa-images" style={{ marginRight: 6 }}></i>Album
            </Link>
            <a href={isLanding ? "#cach-dat-mon" : "/#cach-dat-mon"}>
              <i className="fa-solid fa-qrcode" style={{ marginRight: 6 }}></i>Đặt món
            </a>
            <Link to="/chat">
              <i className="fa-solid fa-robot" style={{ marginRight: 6 }}></i>AI Tư vấn
            </Link>
          </nav>
        </div>
      </header>

      <main id="main-content">
        <PageTransition transitionKey={location.pathname}>
          <Outlet />
        </PageTransition>
      </main>

      {/* Giỏ hàng nổi toàn cục — luôn hiển thị trên mọi trang khi có món */}
      <CustomerFloatingCart />
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
      { path: "menu", element: <CustomerMenuPage /> },
      { path: "chat", element: <ChatPage /> },
      { path: "orders/:orderCode", element: <OrderStatusPage /> },
      { path: "album", element: <RestaurantAlbumPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
