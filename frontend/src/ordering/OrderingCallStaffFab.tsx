import { useCallback, useState } from "react";
import { useI18n } from "@cmc/i18n";
import { BellRing } from "lucide-react";
import { requestTableAssistance } from "../services/orderService";
import { useOrderingSession } from "./OrderingSessionProvider";

const COOLDOWN_MS = 45_000;

export function OrderingCallStaffFab() {
  const { t } = useI18n();
  const { context } = useOrderingSession();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [cooldownUntil, setCooldownUntil] = useState(0);

  const onCooldown = Date.now() < cooldownUntil;

  const handleCall = useCallback(async () => {
    if (busy || onCooldown) return;
    setBusy(true);
    setNotice("");
    try {
      await requestTableAssistance(context.sessionId, context.sessionToken, {
        note: t("Yêu cầu gọi nhân viên"),
      });
      setNotice(t("Đã gửi yêu cầu hỗ trợ tới nhân viên. Vui lòng chờ trong giây lát."));
      setCooldownUntil(Date.now() + COOLDOWN_MS);
    } catch {
      setNotice(t("Không gửi được yêu cầu hỗ trợ."));
    } finally {
      setBusy(false);
    }
  }, [busy, context.sessionId, context.sessionToken, onCooldown, t]);

  return (
    <div className="ordering-call-staff-wrap">
      {notice ? (
        <p className="ordering-call-staff-notice" role="status">
          {notice}
        </p>
      ) : null}
      <button
        aria-label={t("Gọi nhân viên hỗ trợ")}
        className="ordering-call-staff-fab"
        disabled={busy || onCooldown}
        onClick={() => void handleCall()}
        type="button"
      >
        <BellRing aria-hidden="true" size={22} />
        <span>{busy ? t("Đang gửi…") : onCooldown ? t("Đã gọi nhân viên") : t("Gọi nhân viên")}</span>
      </button>
    </div>
  );
}
