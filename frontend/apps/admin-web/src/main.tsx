import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { AuthProvider, ProtectedRoute } from "@cmc/auth";
import {
  LoginPage,
  NotFoundPage,
  OperationsLayout,
  StatePanel,
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
  { to: "/settings", label: "Cài đặt" },
];

const staffLinks = [
  { to: "/staff", label: "Đơn hàng" },
  { to: "/staff/serve", label: "Phục vụ" },
  { to: "/staff/tables", label: "Bàn" },
  { to: "/staff/payments", label: "Thanh toán" },
];

const kitchenLinks = [
  { to: "/kitchen", label: "Bảng bếp" },
  { to: "/kitchen/history", label: "Lịch sử" },
];

const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <LoginPage
        portalName="CMC Operations"
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
      {
        path: "settings",
        element: <StatePanel title="Cài đặt" message="Chưa có API settings trong contract hiện tại." />,
      },
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
      { path: "orders", element: <StaffOrdersPage /> },
      { path: "serve", element: <StaffOrdersPage /> },
      {
        path: "tables",
        element: (
          <StatePanel
            title="Trạng thái bàn"
            message="Backend hiện chỉ có endpoint tra cứu từng mã bàn."
          />
        ),
      },
      {
        path: "payments",
        element: (
          <StatePanel
            title="Thanh toán"
            message="Contract chưa có endpoint cập nhật payment status độc lập."
          />
        ),
      },
    ],
  },
  {
    path: "/kitchen",
    element: (
      <ProtectedRoute allowedRoles={["Kitchen", "Admin"]}>
        <OperationsLayout title="Bảng bếp" subtitle="Kitchen Realtime" links={kitchenLinks} />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <KitchenPage /> },
      { path: "board", element: <KitchenPage /> },
      {
        path: "history",
        element: (
          <StatePanel
            title="Lịch sử bếp"
            message="Contract hiện tại chưa cung cấp endpoint lịch sử riêng."
          />
        ),
      },
    ],
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
