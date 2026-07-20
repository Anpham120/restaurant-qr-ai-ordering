import { openDineInSession, resolveTableQr } from "../services/tableSessionService";
import { saveOrderContext } from "../components/customer/customerMenuStorage";
import type { SessionCapability } from "./sessionCapabilityStore";
import { orderingPath } from "./orderingRoutes";

export type SessionRecoveryResult =
  | { status: "open"; capability: SessionCapability }
  | { status: "expired" | "invalid" | "error" };

export function appendQrToSessionPath(path: string, qrToken: string): string {
  const url = new URL(path, "http://local");
  url.searchParams.set("qr", qrToken);
  return `${url.pathname}${url.search}`;
}

export function replaceSessionInPath(pathname: string, nextSessionId: string): string {
  const marker = "/table-session/";
  const start = pathname.indexOf(marker);
  if (start < 0) {
    return orderingPath(nextSessionId);
  }

  const rest = pathname.slice(start + marker.length);
  const slash = rest.indexOf("/");
  const suffix = slash >= 0 ? rest.slice(slash + 1) : "menu";
  return orderingPath(nextSessionId, suffix);
}

export async function recoverTableSession(
  qrToken: string,
  tableCode?: string | null,
): Promise<SessionRecoveryResult> {
  try {
    const resolvedTableCode = tableCode?.trim()
      ? tableCode.trim()
      : (await resolveTableQr(qrToken)).tableCode;
    const result = await openDineInSession(qrToken, resolvedTableCode);
    if (result.status !== "open") {
      return { status: result.status === "expired" ? "expired" : "invalid" };
    }

    const capability: SessionCapability = {
      qrToken,
      tableCode: result.session.tableCode ?? resolvedTableCode,
      sessionId: result.session.sessionId,
      sessionToken: result.session.tableSessionToken,
    };
    saveOrderContext(capability);
    return { status: "open", capability };
  } catch {
    return { status: "error" };
  }
}
