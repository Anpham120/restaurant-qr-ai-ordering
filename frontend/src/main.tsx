import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import App from "./App";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminMenuPage } from "./pages/AdminMenuPage";
import { AdminOrdersPage } from "./pages/AdminOrdersPage";
import { AdminTablesPage } from "./pages/AdminTablesPage";
import { CartPage } from "./pages/CartPage";
import { ChatPage } from "./pages/ChatPage";
import { CustomerHomePage } from "./pages/CustomerHomePage";
import { KitchenPage } from "./pages/KitchenPage";
import { LoginPage } from "./pages/LoginPage";
import { MenuPage } from "./pages/MenuPage";
import { OrderStatusPage } from "./pages/OrderStatusPage";
import { StaffOrdersPage } from "./pages/StaffOrdersPage";
import { TableEntryPage } from "./pages/TableEntryPage";
import "./styles.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <CustomerHomePage /> },
      { path: "table/:tableCode", element: <TableEntryPage /> },
      { path: "menu", element: <MenuPage /> },
      { path: "cart", element: <CartPage /> },
      { path: "orders/:orderCode", element: <OrderStatusPage /> },
      { path: "chat", element: <ChatPage /> },
      { path: "login", element: <LoginPage /> },
      { path: "admin", element: <AdminDashboardPage /> },
      { path: "admin/menu", element: <AdminMenuPage /> },
      { path: "admin/orders", element: <AdminOrdersPage /> },
      { path: "admin/tables", element: <AdminTablesPage /> },
      { path: "staff/orders", element: <StaffOrdersPage /> },
      { path: "kitchen", element: <KitchenPage /> },
    ],
  },
]);

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);

