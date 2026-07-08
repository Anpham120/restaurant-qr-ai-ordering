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
import { StaffHomePage } from "../../../src/pages/StaffHomePage";
import { StaffOrdersPage } from "../../../src/pages/StaffOrdersPage";
import { StaffPaymentsPage } from "../../../src/pages/StaffPaymentsPage";
import { ClipboardList, CreditCard, Users } from "lucide-react";

const links = [
  { to: "/", label: "Tổng quan", icon: <Users size={18} /> },
  { to: "/orders", label: "Đơn hàng", icon: <ClipboardList size={18} /> },
  { to: "/payments", label: "Thu ngân", icon: <CreditCard size={18} /> },
];

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage portalName="Staff Portal" allowedRoles={["Staff", "Admin"]} />,
  },
  { path: "/unauthorized", element: <UnauthorizedPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute allowedRoles={["Staff", "Admin"]}>
        <OperationsLayout title="Lễ tân / phục vụ" subtitle="Điều phối sảnh và thu ngân" links={links} />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <StaffHomePage /> },
      { path: "orders", element: <StaffOrdersPage /> },
      { path: "payments", element: <StaffPaymentsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);
