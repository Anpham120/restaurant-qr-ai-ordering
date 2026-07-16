import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  Navigate,
  RouterProvider,
  createBrowserRouter,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { AuthProvider, ProtectedRoute, useAuth } from "@cmc/auth";
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
import { AdminTableSessionsPage } from "../../../src/pages/admin/AdminTableSessionsPage";
import { AdminCategoriesPage } from "../../../src/pages/admin/AdminCategoriesPage";
import { AdminUserManagementPage } from "../../../src/pages/admin/AdminUserManagementPage";
import { AdminPromotionsPage } from "../../../src/pages/admin/AdminPromotionsPage";
import { AdminLoyaltyPage } from "../../../src/pages/admin/AdminLoyaltyPage";
import { AdminReportsPage } from "../../../src/pages/admin/AdminReportsPage";
import { RoleAccessPage } from "../../../src/pages/admin/RoleAccessPage";
import { KitchenHomePage } from "../../../src/pages/KitchenHomePage";
import { KitchenPage } from "../../../src/pages/KitchenPage";
import { StaffHomePage } from "../../../src/pages/StaffHomePage";
import { StaffOrdersPage } from "../../../src/pages/StaffOrdersPage";
import { StaffPaymentsPage } from "../../../src/pages/StaffPaymentsPage";
import { AdminInvoicesPage } from "../../../src/pages/AdminInvoicesPage";
import {
  LayoutDashboard, BookOpen, Tag, ShoppingBag, Receipt,
  QrCode, Users, ClipboardList, CreditCard, ChefHat,
  BadgePercent, Star, BarChart3, Armchair, ShieldCheck,
} from "lucide-react";

const roleRedirects = {
  Admin: "/",
  Staff: "/staff",
  Kitchen: "/kitchen",
} as const;

const adminLinks = [
  { to: "/", label: "Tổng quan", icon: <LayoutDashboard size={18} /> },
  { to: "/orders", label: "Đơn hàng", icon: <ShoppingBag size={18} />, section: "Vận hành" },
  { to: "/sessions", label: "Phiên bàn", icon: <Armchair size={18} />, section: "Vận hành" },
  { to: "/invoices", label: "Hóa đơn", icon: <Receipt size={18} />, section: "Vận hành" },
  { to: "/menu", label: "Thực đơn", icon: <BookOpen size={18} />, section: "Thực đơn" },
  { to: "/categories", label: "Danh mục", icon: <Tag size={18} />, section: "Thực đơn" },
  { to: "/promotions", label: "Khuyến mãi", icon: <BadgePercent size={18} />, section: "Khách hàng" },
  { to: "/loyalty", label: "Tích điểm", icon: <Star size={18} />, section: "Khách hàng" },
  { to: "/reports", label: "Báo cáo", icon: <BarChart3 size={18} />, section: "Hệ thống" },
  { to: "/access", label: "Phân quyền", icon: <ShieldCheck size={18} />, section: "Hệ thống" },
  { to: "/tables", label: "Bàn & QR", icon: <QrCode size={18} />, section: "Hệ thống" },
  { to: "/users", label: "Người dùng", icon: <Users size={18} />, section: "Hệ thống" },
];

const staffLinks = [
  { to: "/staff", label: "Tổng quan", icon: <Users size={18} /> },
  { to: "/staff/orders", label: "Đơn hàng", icon: <ClipboardList size={18} /> },
  { to: "/staff/payments", label: "Thu ngân", icon: <CreditCard size={18} /> },
];

const kitchenLinks = [
  { to: "/kitchen", label: "Tổng quan", icon: <ChefHat size={18} /> },
  { to: "/kitchen/board", label: "Bảng bếp", icon: <ClipboardList size={18} /> },
];

function getOrderingBaseUrl() {
  const configured = import.meta.env.VITE_ORDERING_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (typeof window === "undefined") {
    return "https://order.cmcrestaurant.app";
  }

  const { origin, hostname, protocol, port } = window.location;
  if (["localhost", "127.0.0.1"].includes(hostname)) {
    return `${protocol}//${hostname}:5177`;
  }
  if (hostname.startsWith("admin.")) {
    return `${protocol}//${hostname.replace(/^admin\./, "order.")}${port ? `:${port}` : ""}`;
  }

  return origin;
}

function CustomerTableRedirect() {
  const { tableCode } = useParams();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const qrToken = searchParams.get("qr");
    const path = qrToken
      ? `/enter/${encodeURIComponent(qrToken)}`
      : `/table/${encodeURIComponent(tableCode ?? "")}`;
    const target = new URL(path, getOrderingBaseUrl());
    window.location.replace(target.toString());
  }, [searchParams, tableCode]);

  return (
    <main className="cmc-redirect-page">
      <h1>Đang mở ứng dụng gọi món</h1>
      <p>Link bàn thuộc ordering app. Hệ thống đang mở đúng domain cho khách.</p>
    </main>
  );
}

function RoleAwareAdminLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="cmc-state" role="status">
        Đang xác minh phiên đăng nhập...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: "/" }} />;
  }

  if (user.role === "Staff") {
    return <Navigate to="/staff" replace />;
  }

  if (user.role === "Kitchen") {
    return <Navigate to="/kitchen" replace />;
  }

  if (user.role !== "Admin") {
    return <Navigate to="/login" replace />;
  }

  return (
    <OperationsLayout
      title="Quản trị CMC"
      subtitle="Bảng điều khiển nhà hàng"
      links={adminLinks}
    />
  );
}

function RoleAwareUnauthorizedPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="cmc-state" role="status">
        Đang xác minh phiên đăng nhập...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === "Admin") {
    return <Navigate to="/" replace />;
  }

  if (user.role === "Staff") {
    return <Navigate to="/staff" replace />;
  }

  if (user.role === "Kitchen") {
    return <Navigate to="/kitchen" replace />;
  }

  return <UnauthorizedPage />;
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
  { path: "/unauthorized", element: <RoleAwareUnauthorizedPage /> },
  {
    path: "/",
    element: <RoleAwareAdminLayout />,
    children: [
      { index: true, element: <AdminDashboardPage /> },
      { path: "menu", element: <AdminMenuPage /> },
      { path: "categories", element: <AdminCategoriesPage /> },
      { path: "orders", element: <AdminOrdersPage /> },
      { path: "invoices", element: <AdminInvoicesPage /> },
      { path: "promotions", element: <AdminPromotionsPage /> },
      { path: "loyalty", element: <AdminLoyaltyPage /> },
      { path: "reports", element: <AdminReportsPage /> },
      { path: "access", element: <RoleAccessPage /> },
      { path: "sessions", element: <AdminTableSessionsPage /> },
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
      { index: true, element: <StaffHomePage /> },
      { path: "orders", element: <StaffOrdersPage /> },
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
    children: [
      { index: true, element: <KitchenHomePage /> },
      { path: "board", element: <KitchenPage /> },
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
