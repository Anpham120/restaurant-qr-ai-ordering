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
import { KitchenPage } from "../../../src/pages/KitchenPage";
import { StaffOrdersPage } from "../../../src/pages/StaffOrdersPage";
import { AdminInvoicesPage } from "../../../src/pages/AdminInvoicesPage";
import { CounterWorkspacePage } from "../../../src/pages/counter/CounterWorkspacePage";
import {
  LayoutDashboard, BookOpen, Tag, ShoppingBag, Receipt,
  QrCode, Users, ClipboardList, ChefHat,
  BadgePercent, Star, BarChart3, Armchair, ShieldCheck,
} from "lucide-react";

const roleRedirects = {
  Admin: "/",
  CounterStaff: "/counter",
  Staff: "/counter",
  Kitchen: "/kitchen/board",
} as const;

const adminLinks = [
  { to: "/", label: "Tổng quan", icon: <LayoutDashboard size={18} /> },
  { to: "/orders", label: "Đơn hàng", icon: <ShoppingBag size={18} />, section: "Vận hành" },
  { to: "/sessions", label: "Phiên bàn", icon: <Armchair size={18} />, section: "Vận hành" },
  { to: "/invoices", label: "Hóa đơn", icon: <Receipt size={18} />, section: "Vận hành" },
  { to: "/counter", label: "Quầy thu ngân", icon: <Receipt size={18} />, section: "Vận hành" },
  { to: "/kitchen/board", label: "Bảng bếp", icon: <ChefHat size={18} />, section: "Vận hành" },
  { to: "/menu", label: "Thực đơn", icon: <BookOpen size={18} />, section: "Danh mục" },
  { to: "/categories", label: "Danh mục", icon: <Tag size={18} />, section: "Danh mục" },
  { to: "/promotions", label: "Khuyến mãi", icon: <BadgePercent size={18} />, section: "Khách hàng" },
  { to: "/loyalty", label: "Tích điểm", icon: <Star size={18} />, section: "Khách hàng" },
  { to: "/reports", label: "Báo cáo", icon: <BarChart3 size={18} />, section: "Hệ thống" },
  { to: "/access", label: "Phân quyền", icon: <ShieldCheck size={18} />, section: "Hệ thống" },
  { to: "/tables", label: "Bàn & QR", icon: <QrCode size={18} />, section: "Hệ thống" },
  { to: "/users", label: "Người dùng", icon: <Users size={18} />, section: "Hệ thống" },
];

const counterLinks = [
  { to: "/counter", label: "Quầy thu ngân", icon: <Receipt size={18} /> },
  { to: "/orders", label: "Đơn hàng", icon: <ClipboardList size={18} /> },
  { to: "/sessions", label: "Phiên bàn", icon: <Armchair size={18} /> },
];

const kitchenLinks = [
  { to: "/kitchen/board", label: "Bảng bếp", icon: <ChefHat size={18} /> },
];

function getOrderingBaseUrl() {
  const configured = import.meta.env.VITE_ORDERING_BASE_URL;
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window === "undefined") return "https://order.cmcrestaurant.app";
  const { origin, hostname, protocol, port } = window.location;
  if (["localhost", "127.0.0.1"].includes(hostname)) return `${protocol}//${hostname}:5177`;
  if (hostname.startsWith("admin.") || hostname.startsWith("ops.")) {
    return `${protocol}//${hostname.replace(/^(admin|ops)\./, "order.")}${port ? `:${port}` : ""}`;
  }
  return origin;
}

function CustomerTableRedirect() {
  const { tableCode } = useParams();
  const [searchParams] = useSearchParams();
  useEffect(() => {
    const qrToken = searchParams.get("qr");
    const path = qrToken ? `/enter/${encodeURIComponent(qrToken)}` : `/table/${encodeURIComponent(tableCode ?? "")}`;
    window.location.replace(new URL(path, getOrderingBaseUrl()).toString());
  }, [searchParams, tableCode]);
  return <main className="cmc-redirect-page"><h1>Đang mở ứng dụng gọi món</h1></main>;
}

function RoleLandingRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="cmc-state" role="status">Đang xác minh phiên đăng nhập...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "Kitchen") return <Navigate to="/kitchen/board" replace />;
  if (user.role === "CounterStaff" || user.role === "Staff") return <Navigate to="/counter" replace />;
  if (user.role === "Admin") return <AdminDashboardPage />;
  return <Navigate to="/login" replace />;
}

function RoleAwareOpsShell() {
  const { user, loading } = useAuth();
  if (loading) return <div className="cmc-state" role="status">Đang xác minh phiên đăng nhập...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "Kitchen") {
    return <OpsShell title="Bảng bếp" subtitle="Theo dõi thời gian thực" links={kitchenLinks} />;
  }
  if (user.role === "CounterStaff" || user.role === "Staff") {
    return <OpsShell title="Quầy vận hành" subtitle="Thu ngân & phiên bàn" links={counterLinks} />;
  }
  if (user.role === "Admin") {
    return <OpsShell title="CMC Operations" subtitle="Vận hành nhà hàng" links={adminLinks} />;
  }
  return <Navigate to="/login" replace />;
}

function OpsShell({ title, subtitle, links }: { title: string; subtitle: string; links: typeof adminLinks }) {
  return <OperationsLayout title={title} subtitle={subtitle} links={links} />;
}

const router = createBrowserRouter([
  { path: "/table/:tableCode", element: <CustomerTableRedirect /> },
  {
    path: "/login",
    element: (
      <LoginPage
        portalName="CMC Operations"
        allowedRoles={["Admin", "CounterStaff", "Staff", "Kitchen"]}
        roleRedirects={roleRedirects}
      />
    ),
  },
  { path: "/unauthorized", element: <UnauthorizedPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute allowedRoles={["Admin", "CounterStaff", "Staff", "Kitchen"]}>
        <RoleAwareOpsShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <RoleLandingRedirect /> },
      { path: "menu", element: <ProtectedRoute allowedRoles={["Admin"]}><AdminMenuPage /></ProtectedRoute> },
      { path: "categories", element: <ProtectedRoute allowedRoles={["Admin"]}><AdminCategoriesPage /></ProtectedRoute> },
      { path: "orders", element: <ProtectedRoute allowedRoles={["Admin", "CounterStaff", "Staff"]}><AdminOrdersPage /></ProtectedRoute> },
      { path: "invoices", element: <ProtectedRoute allowedRoles={["Admin", "CounterStaff", "Staff"]}><AdminInvoicesPage /></ProtectedRoute> },
      { path: "promotions", element: <ProtectedRoute allowedRoles={["Admin"]}><AdminPromotionsPage /></ProtectedRoute> },
      { path: "loyalty", element: <ProtectedRoute allowedRoles={["Admin"]}><AdminLoyaltyPage /></ProtectedRoute> },
      { path: "reports", element: <ProtectedRoute allowedRoles={["Admin"]}><AdminReportsPage /></ProtectedRoute> },
      { path: "access", element: <ProtectedRoute allowedRoles={["Admin"]}><RoleAccessPage /></ProtectedRoute> },
      { path: "sessions", element: <ProtectedRoute allowedRoles={["Admin", "CounterStaff", "Staff"]}><AdminTableSessionsPage /></ProtectedRoute> },
      { path: "tables", element: <ProtectedRoute allowedRoles={["Admin"]}><AdminTablesPage /></ProtectedRoute> },
      { path: "users", element: <ProtectedRoute allowedRoles={["Admin"]}><AdminUserManagementPage /></ProtectedRoute> },
      { path: "counter", element: <ProtectedRoute allowedRoles={["Admin", "CounterStaff", "Staff"]}><CounterWorkspacePage /></ProtectedRoute> },
      { path: "staff/orders", element: <Navigate to="/orders" replace /> },
      { path: "staff/payments", element: <Navigate to="/counter" replace /> },
      { path: "staff", element: <Navigate to="/counter" replace /> },
      { path: "kitchen", element: <Navigate to="/kitchen/board" replace /> },
      { path: "kitchen/board", element: <ProtectedRoute allowedRoles={["Admin", "Kitchen"]}><KitchenPage /></ProtectedRoute> },
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
