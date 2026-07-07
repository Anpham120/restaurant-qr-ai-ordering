import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  RouterProvider,
  createBrowserRouter,
  useParams,
  useSearchParams,
} from "react-router-dom";
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
import { AdminPromotionsPage } from "../../../src/pages/admin/AdminPromotionsPage";
import { AdminLoyaltyPage } from "../../../src/pages/admin/AdminLoyaltyPage";
import { AdminReportsPage } from "../../../src/pages/admin/AdminReportsPage";
import { KitchenPage } from "../../../src/pages/KitchenPage";
import { StaffOrdersPage } from "../../../src/pages/StaffOrdersPage";
import { StaffPaymentsPage } from "../../../src/pages/StaffPaymentsPage";
import { AdminInvoicesPage } from "../../../src/pages/AdminInvoicesPage";
import {
  LayoutDashboard, BookOpen, Tag, ShoppingBag, Receipt,
  QrCode, Users, ClipboardList, CreditCard, ChefHat,
  BadgePercent, Star, BarChart3,
} from "lucide-react";

const roleRedirects = {
  Admin: "/",
  Staff: "/staff",
  Kitchen: "/kitchen",
} as const;

const adminLinks = [
  { to: "/", label: "Tổng quan", icon: <LayoutDashboard size={18} /> },
  { to: "/menu", label: "Thực đơn", icon: <BookOpen size={18} /> },
  { to: "/categories", label: "Danh mục", icon: <Tag size={18} /> },
  { to: "/orders", label: "Đơn hàng", icon: <ShoppingBag size={18} /> },
  { to: "/invoices", label: "Hóa đơn", icon: <Receipt size={18} /> },
  { to: "/promotions", label: "Khuyến mãi", icon: <BadgePercent size={18} /> },
  { to: "/loyalty", label: "Tích điểm", icon: <Star size={18} /> },
  { to: "/reports", label: "Báo cáo", icon: <BarChart3 size={18} /> },
  { to: "/tables", label: "Bàn & QR", icon: <QrCode size={18} /> },
  { to: "/users", label: "Người dùng", icon: <Users size={18} /> },
];

const staffLinks = [
  { to: "/staff", label: "Đơn hàng", icon: <ClipboardList size={18} /> },
  { to: "/staff/payments", label: "Thu ngân", icon: <CreditCard size={18} /> },
];

const kitchenLinks = [{ to: "/kitchen", label: "Bảng bếp", icon: <ChefHat size={18} /> }];

function getCustomerBaseUrl() {
  const configured = import.meta.env.VITE_CUSTOMER_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (typeof window === "undefined") {
    return "https://customer.cmcrestaurant.app";
  }

  const { origin, hostname, protocol, port } = window.location;
  if (hostname.startsWith("admin.")) {
    return `${protocol}//${hostname.replace(/^admin\./, "customer.")}${port ? `:${port}` : ""}`;
  }

  return origin;
}

function CustomerTableRedirect() {
  const { tableCode } = useParams();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const target = new URL(`/table/${encodeURIComponent(tableCode ?? "")}`, getCustomerBaseUrl());
    const qrToken = searchParams.get("qr");
    if (qrToken) {
      target.searchParams.set("qr", qrToken);
    }
    window.location.replace(target.toString());
  }, [searchParams, tableCode]);

  return (
    <main className="cmc-redirect-page">
      <h1>Đang chuyển sang trang khách hàng</h1>
      <p>Link bàn thuộc customer portal. Hệ thống đang mở đúng domain cho khách.</p>
    </main>
  );
}

const router = createBrowserRouter([
  { path: "/table/:tableCode", element: <CustomerTableRedirect /> },
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
        <OperationsLayout
          title="Quản trị CMC"
          subtitle="Bảng điều khiển nhà hàng"
          links={adminLinks}
        />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <AdminDashboardPage /> },
      { path: "menu", element: <AdminMenuPage /> },
      { path: "categories", element: <AdminCategoriesPage /> },
      { path: "orders", element: <AdminOrdersPage /> },
      { path: "invoices", element: <AdminInvoicesPage /> },
      { path: "promotions", element: <AdminPromotionsPage /> },
      { path: "loyalty", element: <AdminLoyaltyPage /> },
      { path: "reports", element: <AdminReportsPage /> },
      { path: "tables", element: <AdminTablesPage /> },
      { path: "users", element: <AdminUserManagementPage /> },
    ],
  },
  {
    path: "/staff",
    element: (
      <ProtectedRoute allowedRoles={["Staff", "Admin"]}>
        <OperationsLayout title="Nhân viên" subtitle="Quản lý phục vụ" links={staffLinks} />
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
        <OperationsLayout title="Bảng bếp" subtitle="Theo dõi thời gian thực" links={kitchenLinks} />
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
