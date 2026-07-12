import { BrandWordmark } from "@cmc/brand-ui";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { OrderingSessionProvider, useOrderingSession, useOrderingSessionBoundary } from "./OrderingSessionProvider";
import { orderingNavigation } from "./orderingRoutes";
import "./ordering-layout.css";

type UnavailableSessionState = "missing" | "invalid" | "expired" | "error";

function SessionState({
  onRetry,
  state,
}: {
  onRetry: () => Promise<void>;
  state: UnavailableSessionState;
}) {
  const copy = state === "expired"
    ? "Phiên bàn đã hết hạn hoặc đã được nhân viên đóng. Vui lòng quét QR tại bàn để mở phiên mới."
    : state === "error"
      ? "Không thể xác minh phiên bàn lúc này. Hãy kiểm tra kết nối và thử lại."
      : state === "missing"
        ? "Liên kết này chưa có quyền truy cập phiên. Vui lòng mở lại bằng mã QR trên bàn."
        : "Phiên trên thiết bị không khớp với liên kết. Vui lòng quét lại mã QR trên bàn.";
  const marketingBaseUrl = import.meta.env.VITE_MARKETING_BASE_URL ?? "https://cmcrestaurant.app";

  return (
    <main className="ordering-state" aria-live="polite">
      <p className="ordering-state-kicker">CMC Restaurant</p>
      <h1>Phiên gọi món chưa sẵn sàng</h1>
      <p>{copy}</p>
      <div className="ordering-state-actions">
        {state === "error" ? <button type="button" onClick={() => void onRetry()}>Thử lại</button> : null}
        <a href="/">Quét QR để bắt đầu</a>
        <a className="ordering-state-secondary" href={marketingBaseUrl}>Trang giới thiệu</a>
      </div>
    </main>
  );
}

function OrderingShell() {
  const { context } = useOrderingSession();
  const base = `/table-session/${context.sessionId}`;

  return (
    <div className="ordering-shell">
      <header className="ordering-header">
        <a className="ordering-brand" href={base}><BrandWordmark /></a>
        <div className="ordering-table" aria-label={`Phiên bàn ${context.tableCode}`}>
          <span>Phiên đang mở</span>
          <strong>{context.tableCode}</strong>
        </div>
      </header>
      <nav className="ordering-nav" aria-label="Điều hướng gọi món">
        {orderingNavigation.map(({ path, label }) => (
          <NavLink key={path} to={path} className={({ isActive }) => isActive ? "active" : undefined}>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <main className="ordering-main"><Outlet /></main>
    </div>
  );
}

function OrderingBoundary() {
  const { sessionId } = useParams();
  if (!sessionId) return <SessionState state="missing" onRetry={async () => {}} />;

  return (
    <OrderingSessionProvider sessionId={sessionId}>
      <OrderingBoundaryContent />
    </OrderingSessionProvider>
  );
}

function OrderingBoundaryContent() {
  const { refresh, state } = useOrderingSessionBoundary();
  if (state === "loading") return <main className="ordering-state">Đang xác minh phiên bàn…</main>;
  if (state !== "ready") return <SessionState state={state} onRetry={refresh} />;
  return <OrderingShell />;
}

export { OrderingBoundary as OrderingLayout };
