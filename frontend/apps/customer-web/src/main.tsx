import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  Link,
  Outlet,
  RouterProvider,
  createBrowserRouter,
  useLocation,
} from "react-router-dom";
import { NotFoundPage, PageTransition } from "@cmc/shared-ui";
import "@cmc/brand-ui/styles.css";
import "@cmc/shared-ui/styles.css";
import "../../../src/styles.css";
import logoUrl from "../../../src/mocks/images/logo.png";
import { CustomerHomePage } from "../../../src/pages/CustomerHomePage";
import { RestaurantAlbumPage } from "../../../src/pages/RestaurantAlbumPage";
import { PublicMenuPreviewPage } from "../../../src/pages/customer/PublicMenuPreviewPage";

function getOrderingBaseUrl() {
  const configured = import.meta.env.VITE_ORDERING_BASE_URL;
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    return `${window.location.protocol}//${window.location.hostname}:5177`;
  }
  return "https://order.cmcrestaurant.app";
}

function OrderingHostRedirect({ preservePath = true }: { preservePath?: boolean }) {
  const location = useLocation();
  const target = new URL(
    preservePath ? `${location.pathname}${location.search}` : "/",
    getOrderingBaseUrl(),
  ).toString();

  useEffect(() => {
    window.location.replace(target);
  }, [target]);

  return (
    <main className="ordering-state">
      <p>Đang mở ứng dụng gọi món…</p>
      <a href={target}>Tiếp tục</a>
    </main>
  );
}

function MarketingLayout() {
  const location = useLocation();

  return (
    <div className="landing-shell">
      <a className="skip-link" href="#main-content">Chuyển đến nội dung chính</a>
      <header className="landing-header">
        <div className="landing-header-inner">
          <Link className="landing-brand" to="/" aria-label="CMC Restaurant - Trang chủ">
            <img className="landing-brand-logo" alt="" src={logoUrl} width="44" height="44" />
            <span className="landing-brand-text" translate="no"><strong>CMC Restaurant</strong><small>Restaurant</small></span>
          </Link>
          <nav className="landing-nav" aria-label="Điều hướng marketing">
            <Link to="/#gioi-thieu">Giới thiệu</Link>
            <Link to="/menu">Thực đơn</Link>
            <Link to="/#danh-gia">Đánh giá</Link>
            <Link to="/album">Album</Link>
          </nav>
        </div>
      </header>
      <main id="main-content">
        <PageTransition transitionKey={location.pathname}><Outlet /></PageTransition>
      </main>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <MarketingLayout />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <CustomerHomePage /> },
      { path: "menu", element: <PublicMenuPreviewPage /> },
      { path: "album", element: <RestaurantAlbumPage /> },
      { path: "scan/:qrToken", element: <OrderingHostRedirect /> },
      { path: "table/:tableCode", element: <OrderingHostRedirect /> },
      { path: "table-session/:sessionId/*", element: <OrderingHostRedirect /> },
      { path: "cart", element: <OrderingHostRedirect preservePath={false} /> },
      { path: "checkout", element: <OrderingHostRedirect preservePath={false} /> },
      { path: "chat", element: <OrderingHostRedirect preservePath={false} /> },
      { path: "orders/:orderCode", element: <OrderingHostRedirect preservePath={false} /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode><RouterProvider router={router} /></StrictMode>,
);
