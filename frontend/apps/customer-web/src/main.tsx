import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Link,
  Navigate,
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
import { RestaurantAlbumPage } from "../../../src/pages/RestaurantAlbumPage";
import { LegacyOrderingRedirect, LegacyOrderTrackingRedirect } from "../../../src/ordering/LegacyOrderingRedirect";
import { OrderingLayout } from "../../../src/ordering/OrderingLayout";
import { OrderingMenuPage } from "../../../src/ordering/OrderingMenuPage";
import { PublicMenuPreviewPage } from "../../../src/ordering/PublicMenuPreviewPage";
import { TableScanPage } from "../../../src/ordering/TableScanPage";
import { SessionOrdersPage } from "../../../src/ordering/SessionOrdersPage";

function MarketingLayout() {
  const location = useLocation();
  const [notice, setNotice] = useState("");
  const showScanNotice = () => setNotice("Vui lòng quét QR tại bàn để sử dụng AI tư vấn và gọi món.");

  return (
    <div className="landing-shell">
      <a className="skip-link" href="#main-content">Chuyển đến nội dung chính</a>
      <header className="landing-header">
        <div className="landing-header-inner">
          <Link className="landing-brand" to="/" aria-label="CMC Restaurant - Trang chủ">
            <img className="landing-brand-logo" alt="" src={logoUrl} width="44" height="44" />
            <span className="landing-brand-text" translate="no"><strong>CMC Restaurant</strong><small>QR Ordering</small></span>
          </Link>
          <nav className="landing-nav" aria-label="Điều hướng marketing">
            <Link to="/#gioi-thieu">Giới thiệu</Link>
            <Link to="/menu">Thực đơn</Link>
            <Link to="/#danh-gia">Đánh giá</Link>
            <Link to="/album">Album</Link>
            <Link to="/#cach-dat-mon">Cách gọi món</Link>
            <button type="button" onClick={showScanNotice}>AI tư vấn</button>
          </nav>
        </div>
      </header>
      {notice ? <p className="landing-scan-notice" role="status">{notice}</p> : null}
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
      { path: "scan/:qrToken", element: <TableScanPage /> },
      { path: "table/:tableCode", element: <TableEntryPage /> },
      { path: "cart", element: <LegacyOrderingRedirect destination="cart" /> },
      { path: "checkout", element: <LegacyOrderingRedirect destination="checkout" /> },
      { path: "chat", element: <LegacyOrderingRedirect destination="ai" /> },
      { path: "orders/:orderCode", element: <LegacyOrderTrackingRedirect /> },
    ],
  },
  {
    path: "/table-session/:sessionId",
    element: <OrderingLayout />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <Navigate replace to="menu" /> },
      { path: "ai", element: <ChatPage /> },
      { path: "menu", element: <OrderingMenuPage /> },
      { path: "cart", element: <CartPage /> },
      { path: "checkout", element: <CartPage /> },
      { path: "orders", element: <SessionOrdersPage /> },
      { path: "orders/:orderCode", element: <OrderStatusPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode><RouterProvider router={router} /></StrictMode>,
);
