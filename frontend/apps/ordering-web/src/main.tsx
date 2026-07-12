import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import { BrandWordmark } from "@cmc/brand-ui";
import { NotFoundPage } from "@cmc/shared-ui";
import "@cmc/shared-ui/styles.css";
import "./ordering-app.css";
import { TableEntryPage } from "../../../src/pages/TableEntryPage";
import { CartPage } from "../../../src/pages/CartPage";
import { OrderStatusPage } from "../../../src/pages/OrderStatusPage";
import { OrderingLayout } from "../../../src/ordering/OrderingLayout";
import { OrderingMenuPage } from "../../../src/ordering/OrderingMenuPage";
import { SessionOrdersPage } from "../../../src/ordering/SessionOrdersPage";
import { TableScanPage } from "../../../src/ordering/TableScanPage";

function OrderingEntryPage() {
  const marketingBaseUrl = import.meta.env.VITE_MARKETING_BASE_URL ?? "https://cmcrestaurant.app";
  return (
    <main className="ordering-entry">
      <section className="ordering-entry-card">
        <BrandWordmark />
        <h1>Quét QR để gọi món</h1>
        <p>Mở camera và quét mã QR trên bàn. Phiên gọi món chỉ hoạt động trên thiết bị đã quét mã.</p>
        <div className="ordering-entry-actions">
          <a href={marketingBaseUrl}>Xem trang giới thiệu nhà hàng</a>
        </div>
      </section>
    </main>
  );
}

function MarketingHostRedirect({ path }: { path: string }) {
  const marketingBaseUrl = import.meta.env.VITE_MARKETING_BASE_URL ?? "https://cmcrestaurant.app";
  const target = new URL(path, marketingBaseUrl).toString();
  useEffect(() => { window.location.replace(target); }, [target]);
  return <main className="ordering-entry"><p>Đang mở trang nhà hàng…</p></main>;
}

const router = createBrowserRouter([
  { path: "/", element: <OrderingEntryPage /> },
  { path: "/enter/:qrToken", element: <TableScanPage /> },
  { path: "/scan/:qrToken", element: <TableScanPage /> },
  { path: "/table/:tableCode", element: <TableEntryPage /> },
  { path: "/menu", element: <MarketingHostRedirect path="/menu" /> },
  { path: "/album", element: <MarketingHostRedirect path="/album" /> },
  {
    path: "/table-session/:sessionId",
    element: <OrderingLayout />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <Navigate replace to="menu" /> },
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
