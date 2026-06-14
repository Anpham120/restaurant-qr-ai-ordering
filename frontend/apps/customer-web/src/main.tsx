import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Link, NavLink, Outlet, RouterProvider, createBrowserRouter, useLocation } from "react-router-dom";
import { NotFoundPage } from "@cmc/shared-ui";
import "@cmc/shared-ui/styles.css";
import "../../../src/styles.css";
import logoUrl from "../../../src/mocks/images/logo.png";
import { CustomerHomePage } from "../../../src/pages/CustomerHomePage";
import { TableEntryPage } from "../../../src/pages/TableEntryPage";
import { MenuPage } from "../../../src/pages/MenuPage";
import { CartPage } from "../../../src/pages/CartPage";
import { OrderStatusPage } from "../../../src/pages/OrderStatusPage";
import { ChatPage } from "../../../src/pages/ChatPage";
import { CustomerAiLauncher } from "../../../src/components/customer/CustomerAiLauncher";

function CustomerLayout(){
  const location=useLocation();
  const [menuOpen,setMenuOpen]=useState(false);
  const isLanding=location.pathname==="/";
  useEffect(()=>setMenuOpen(false),[location.pathname,location.hash]);
  return <div className={`customer-app-shell${isLanding?" landing-shell":""}`}>
    <a className="skip-link" href="#main-content">Chuyển đến nội dung chính</a>
    <header className="customer-topbar">
      <Link className="customer-brand" to="/" aria-label="CMC Restaurant - Trang chủ"><img className="customer-brand-logo" alt="" src={logoUrl} width="54" height="54"/><span translate="no"><strong>CMC Restaurant</strong><small>QR AI Ordering</small></span></Link>
      <button className="customer-menu-toggle" type="button" aria-expanded={menuOpen} aria-controls="customer-navigation" aria-label={menuOpen?"Đóng menu":"Mở menu"} onClick={()=>setMenuOpen((open)=>!open)}><span/><span/><span/></button>
      <nav className={`customer-nav${menuOpen?" open":""}`} id="customer-navigation" aria-label="Điều hướng khách hàng">
        <NavLink to="/menu">Thực đơn</NavLink>
        <a href="/#trai-nghiem">Trải nghiệm</a>
        <a href="/#cach-goi-mon">Cách gọi món</a>
        <NavLink to="/chat">Hỏi AI</NavLink>
        {!isLanding?<NavLink to="/cart">Giỏ hàng</NavLink>:null}
      </nav>
    </header>
    <main className="customer-content" id="main-content"><Outlet/></main>
    <CustomerAiLauncher hidden={menuOpen}/>
  </div>
}
const router=createBrowserRouter([{path:"/",element:<CustomerLayout/>,errorElement:<NotFoundPage/>,children:[{index:true,element:<CustomerHomePage/>},{path:"table/:tableCode",element:<TableEntryPage/>},{path:"menu",element:<MenuPage/>},{path:"cart",element:<CartPage/>},{path:"orders/:orderCode",element:<OrderStatusPage/>},{path:"chat",element:<ChatPage/>},{path:"*",element:<NotFoundPage/>}]}]);
createRoot(document.getElementById("root")!).render(<StrictMode><RouterProvider router={router}/></StrictMode>);
