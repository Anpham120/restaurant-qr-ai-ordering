import { BrandWordmark } from "@cmc/brand-ui";
import { LanguageSwitcher, useI18n } from "@cmc/i18n";
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
  const { t } = useI18n();
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
      <LanguageSwitcher />
      <h1>{t("Phiên gọi món chưa sẵn sàng")}</h1>
      <p>{t(copy)}</p>
      <div className="ordering-state-actions">
        {state === "error" ? <button type="button" onClick={() => void onRetry()}>{t("Thử lại")}</button> : null}
        <a href="/">{t("Quét QR để bắt đầu")}</a>
        <a className="ordering-state-secondary" href={marketingBaseUrl}>{t("Trang giới thiệu")}</a>
      </div>
    </main>
  );
}

function OrderingShell() {
  const { t } = useI18n();
  const { context } = useOrderingSession();
  const base = `/table-session/${context.sessionId}`;

  return (
    <div className="ordering-shell">
      <header className="ordering-header">
        <a className="ordering-brand" href={base}><BrandWordmark /></a>
        <LanguageSwitcher />
        <div className="ordering-table" aria-label={t("Phiên bàn {table}", { table: context.tableCode })}>
          <span>{t("Phiên đang mở")}</span>
          <strong>{context.tableCode}</strong>
        </div>
      </header>
      <nav className="ordering-nav" aria-label={t("Điều hướng gọi món")}>
        {orderingNavigation.map(({ path, label }) => (
          <NavLink key={path} to={path} className={({ isActive }) => isActive ? "active" : undefined}>
            <span>{t(label)}</span>
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
  const { t } = useI18n();
  const { refresh, state } = useOrderingSessionBoundary();
  if (state === "loading") return <main className="ordering-state">{t("Đang xác minh phiên bàn…")}</main>;
  if (state !== "ready") return <SessionState state={state} onRetry={refresh} />;
  return <OrderingShell />;
}

export { OrderingBoundary as OrderingLayout };
