import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { AuthProvider, ProtectedRoute } from "@cmc/auth";
import {
  LoginPage,
  NotFoundPage,
  OperationsLayout,
  UnauthorizedPage,
} from "@cmc/shared-ui";
import "@cmc/shared-ui/styles.css";
import "../../../src/styles.css";
import { AdminDashboardPage } from "../../../src/pages/AdminDashboardPage";
import { AdminMenuPage } from "../../../src/pages/AdminMenuPage";
import { AdminOrdersPage } from "../../../src/pages/AdminOrdersPage";
import { AdminTablesPage } from "../../../src/pages/AdminTablesPage";
import { AdminCategoriesPage } from "../../../src/pages/admin/AdminCategoriesPage";
import { AdminUserManagementPage } from "../../../src/pages/admin/AdminUserManagementPage";
import { KitchenPage } from "../../../src/pages/KitchenPage";
import { StaffOrdersPage } from "../../../src/pages/StaffOrdersPage";
import { StaffPaymentsPage } from "../../../src/pages/StaffPaymentsPage";

const roleRedirects = {
  Admin: "/",
  Staff: "/staff",
  Kitchen: "/kitchen",
} as const;

const adminLinks = [
  { to: "/", label: "Tổng quan" },
  { to: "/menu", label: "Thực đơn" },
  { to: "/categories", label: "Danh mục" },
  { to: "/orders", label: "Đơn hàng" },
  { to: "/tables", label: "Bàn & QR" },
  { to: "/users", label: "Người dùng" },
];

const staffLinks = [
  { to: "/staff", label: "Đơn hàng" },
  { to: "/staff/payments", label: "Thu ngân" },
];

const kitchenLinks = [{ to: "/kitchen", label: "Bảng bếp" }];

const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <LoginPage
        portalName="Admin Portal"
        allowedRoles={["Admin", "Staff", "Kitchen"]}
        roleRedirects={roleRedirects}
      />
    ),
  },
  { path: "/unauthorized", element: <UnauthorizedPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute allowedRoles={["Admin"]}>
        <OperationsLayout title="CMC Admin" subtitle="Restaurant Control" links={adminLinks} />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <AdminDashboardPage /> },
      { path: "menu", element: <AdminMenuPage /> },
      { path: "categories", element: <AdminCategoriesPage /> },
      { path: "orders", element: <AdminOrdersPage /> },
      { path: "tables", element: <AdminTablesPage /> },
      { path: "users", element: <AdminUserManagementPage /> },
    ],
  },
  {
    path: "/staff",
    element: (
      <ProtectedRoute allowedRoles={["Staff", "Admin"]}>
        <OperationsLayout title="Staff Portal" subtitle="Service Operations" links={staffLinks} />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <StaffOrdersPage /> },
      { path: "payments", element: <StaffPaymentsPage /> },
    ],
  },
  {
    path: "/kitchen",
    element: (
      <ProtectedRoute allowedRoles={["Kitchen", "Admin"]}>
        <OperationsLayout title="Bảng bếp" subtitle="Kitchen Realtime" links={kitchenLinks} />
      </ProtectedRoute>
    ),
    children: [{ index: true, element: <KitchenPage /> }],
  },
  { path: "*", element: <NotFoundPage /> },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);
