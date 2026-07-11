import { NavLink, Outlet, useParams } from "react-router-dom";
import { CustomerFloatingCart } from "../components/customer/CustomerFloatingCart";
import { OrderingSessionProvider, useOrderingSession, useOrderingSessionBoundary } from "./OrderingSessionProvider";
import "./ordering-layout.css";

function SessionState({ state }: { state: "invalid" | "expired" | "error" }) {
  const copy = state === "expired"
    ? "Phiên bàn đã hết hạn hoặc đã được nhân viên đóng. Vui lòng quét QR tại bàn để mở phiên mới."
    : state === "error"
      ? "Không thể xác minh phiên bàn lúc này. Hãy thử lại hoặc quét QR tại bàn."
      : "Bạn cần quét QR tại bàn để sử dụng AI tư vấn và gọi món.";

  return (
    <main className="ordering-state" aria-live="polite">
      <p className="ordering-state-kicker">CMC Restaurant</p>
      <h1>Phiên gọi món chưa sẵn sàng</h1>
      <p>{copy}</p>
      <a href="/">Về trang giới thiệu</a>
    </main>
  );
}

function OrderingShell() {
  const { context } = useOrderingSession();
  const base = `/table-session/${context.sessionId}`;
  const tabs = [
    ["ai", "AI"],
    ["menu", "Thực đơn"],
    ["cart", "Giỏ hàng"],
    ["checkout", "Thanh toán"],
    ["orders", "Món đã gọi"],
  ] as const;

  return (
    <div className="ordering-shell">
      <header className="ordering-header">
        <a className="ordering-brand" href={base}>
          <strong>CMC</strong>
          <span>QR Ordering</span>
        </a>
        <div className="ordering-table" aria-label={`Phiên bàn ${context.tableCode}`}>
          <span>Bàn</span>
          <strong>{context.tableCode}</strong>
        </div>
      </header>
      <nav className="ordering-nav" aria-label="Điều hướng gọi món">
        {tabs.map(([path, label]) => (
          <NavLink key={path} to={path} className={({ isActive }) => isActive ? "active" : undefined}>
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="ordering-main">
        <Outlet />
      </main>
      <CustomerFloatingCart />
    </div>
  );
}

function OrderingBoundary() {
  const { sessionId } = useParams();
  if (!sessionId) return <SessionState state="invalid" />;

  return (
    <OrderingSessionProvider sessionId={sessionId}>
      <OrderingBoundaryContent />
    </OrderingSessionProvider>
  );
}

function OrderingBoundaryContent() {
  const { state } = useOrderingSessionBoundary();
  if (state === "loading") return <main className="ordering-state">Đang xác minh phiên bàn…</main>;
  if (state !== "ready") return <SessionState state={state} />;
  return <OrderingShell />;
}

export { OrderingBoundary as OrderingLayout };
