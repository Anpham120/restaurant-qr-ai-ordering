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
import { KitchenHomePage } from "../../../src/pages/KitchenHomePage";
import { KitchenPage } from "../../../src/pages/KitchenPage";
import { ChefHat, ClipboardList } from "lucide-react";

const links = [
  { to: "/", label: "Tổng quan", icon: <ChefHat size={18} /> },
  { to: "/board", label: "Bảng bếp", icon: <ClipboardList size={18} /> },
];

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage portalName="Kitchen Portal" allowedRoles={["Kitchen", "Admin"]} />,
  },
  { path: "/unauthorized", element: <UnauthorizedPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute allowedRoles={["Kitchen", "Admin"]}>
        <OperationsLayout title="Nhà bếp" subtitle="Chế biến món theo thời gian thực" links={links} />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <KitchenHomePage /> },
      { path: "board", element: <KitchenPage /> },
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
