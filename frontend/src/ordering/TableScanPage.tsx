import { useEffect, useState } from "react";
import { LanguageSwitcher, useI18n } from "@cmc/i18n";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { clearMenuCart, loadOrderContext, saveOrderContext } from "../components/customer/customerMenuStorage";
import { openDineInSession, resolveTableQr } from "../services/tableSessionService";

type ScanState = "loading" | "invalid" | "expired" | "error";

export function TableScanPage({ tableCode }: { tableCode?: string }) {
  const { t } = useI18n();
  const { qrToken: qrTokenFromPath } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [state, setState] = useState<ScanState>("loading");
  const qrToken = qrTokenFromPath ?? searchParams.get("qr") ?? undefined;

  useEffect(() => {
    const activeQrToken = qrToken;
    if (!activeQrToken) {
      setState("invalid");
      return;
    }

    let active = true;
    async function enterOrdering(token: string) {
      try {
        const resolved = tableCode ? { tableCode } : await resolveTableQr(token);
        const result = await openDineInSession(token, resolved.tableCode);
        if (!active) return;

        if (result.status !== "open") {
          setState(result.status === "expired" ? "expired" : result.status === "error" ? "error" : "invalid");
          return;
        }

        const previous = loadOrderContext();
        if (previous.sessionId && previous.sessionId !== result.session.sessionId) {
          clearMenuCart();
        }
        saveOrderContext({
          tableCode: result.session.tableCode ?? resolved.tableCode,
          qrToken: token,
          sessionId: result.session.sessionId,
          sessionToken: result.session.tableSessionToken,
        });
        navigate(`/table-session/${result.session.sessionId}/menu`, { replace: true });
      } catch {
        if (active) setState("error");
      }
    }

    void enterOrdering(activeQrToken);
    return () => { active = false; };
  }, [navigate, qrToken, tableCode]);

  const copy = state === "expired"
    ? "Phiên bàn này đã hết hạn. Vui lòng quét lại QR tại bàn."
    : state === "error"
      ? "Không thể kết nối phiên bàn. Vui lòng thử lại hoặc nhờ nhân viên hỗ trợ."
      : "Mã QR không hợp lệ hoặc không còn hoạt động.";

  return (
    <main className="ordering-state" aria-live="polite">
      <LanguageSwitcher />
      {state === "loading" ? <p>{t("Đang mở phiên gọi món…")}</p> : <><h1>{t("Không thể mở phiên bàn")}</h1><p>{t(copy)}</p><a href="/">{t("Về trang giới thiệu")}</a></>}
    </main>
  );
}
