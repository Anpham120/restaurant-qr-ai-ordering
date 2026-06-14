import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { AuthProvider, ProtectedRoute } from "@cmc/auth";
import App from "./App";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminMenuPage } from "./pages/AdminMenuPage";
import { AdminOrdersPage } from "./pages/AdminOrdersPage";
import { AdminTablesPage } from "./pages/AdminTablesPage";
import { AdminCategoriesPage } from "./pages/admin/AdminCategoriesPage";
import { AdminUserManagementPage } from "./pages/admin/AdminUserManagementPage";
import { CartPage } from "./pages/CartPage";
import { ChatPage } from "./pages/ChatPage";
import { CustomerHomePage } from "./pages/CustomerHomePage";
import { KitchenPage } from "./pages/KitchenPage";
import { LoginPage } from "./pages/LoginPage";
import { MenuPage } from "./pages/MenuPage";
import { OrderStatusPage } from "./pages/OrderStatusPage";
import { StaffOrdersPage } from "./pages/StaffOrdersPage";
import { TableEntryPage } from "./pages/TableEntryPage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";
import "./styles.css";

const adminOnly = ["Admin"] as const;
const staffOrAdmin = ["Staff", "Admin"] as const;
const kitchenOrAdmin = ["Kitchen", "Admin"] as const;

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
      { path: "unauthorized", element: <UnauthorizedPage /> },
      {
        path: "admin",
        element: (
          <ProtectedRoute allowedRoles={[...adminOnly]}>
            <AdminDashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "admin/menu",
        element: (
          <ProtectedRoute allowedRoles={[...adminOnly]}>
            <AdminMenuPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "admin/orders",
        element: (
          <ProtectedRoute allowedRoles={[...staffOrAdmin]}>
            <AdminOrdersPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "admin/tables",
        element: (
          <ProtectedRoute allowedRoles={[...adminOnly]}>
            <AdminTablesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "admin/categories",
        element: (
          <ProtectedRoute allowedRoles={[...adminOnly]}>
            <AdminCategoriesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "admin/users",
        element: (
          <ProtectedRoute allowedRoles={[...adminOnly]}>
            <AdminUserManagementPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "staff/orders",
        element: (
          <ProtectedRoute allowedRoles={[...staffOrAdmin]}>
            <StaffOrdersPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "kitchen",
        element: (
          <ProtectedRoute allowedRoles={[...kitchenOrAdmin]}>
            <KitchenPage />
          </ProtectedRoute>
        ),
      },
    ],
  },
]);

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);

