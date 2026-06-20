import { StrictMode } from "react"; import { createRoot } from "react-dom/client"; import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { AuthProvider, ProtectedRoute } from "@cmc/auth"; import { LoginPage, NotFoundPage, OperationsLayout, UnauthorizedPage } from "@cmc/shared-ui"; import "@cmc/shared-ui/styles.css"; import "../../../src/styles.css";
import { StaffOrdersPage } from "../../../src/pages/StaffOrdersPage";
import { StaffPaymentsPage } from "../../../src/pages/StaffPaymentsPage";
const links=[{to:"/",label:"Đơn hàng"},{to:"/payments",label:"Thu ngân"}];
const router=createBrowserRouter([{path:"/login",element:<LoginPage portalName="Staff Portal" allowedRoles={["Staff","Admin"]}/>},{path:"/unauthorized",element:<UnauthorizedPage/>},{path:"/",element:<ProtectedRoute allowedRoles={["Staff","Admin"]}><OperationsLayout title="Staff Portal" subtitle="Service Operations" links={links}/></ProtectedRoute>,children:[{index:true,element:<StaffOrdersPage/>},{path:"payments",element:<StaffPaymentsPage/>},{path:"*",element:<NotFoundPage/>}]}]);
createRoot(document.getElementById("root")!).render(<StrictMode><AuthProvider><RouterProvider router={router}/></AuthProvider></StrictMode>);
