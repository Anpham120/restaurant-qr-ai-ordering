import { ApiError } from "@cmc/api-client";
import { api } from "./apiClient";

type TableSession = Awaited<ReturnType<typeof api.tables.openSession>>;

export type OpenDineInSessionResult =
  | { status: "open"; session: TableSession }
  | { status: "expired" }
  | { status: "invalid" }
  | { status: "error" };

export type ValidateDineInSessionResult =
  | { status: "open"; session: Awaited<ReturnType<typeof api.tables.getSession>> }
  | { status: "expired" }
  | { status: "invalid" }
  | { status: "error" };

export async function openDineInSession(
  qrToken: string,
  tableCode: string,
): Promise<OpenDineInSessionResult> {
  try {
    const session = await api.tables.openSession({ qrToken, tableCode });
    return { status: "open", session };
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 410 || error.code === "TABLE_SESSION_EXPIRED") {
        return { status: "expired" };
      }

      if (
        error.code === "QR_NOT_FOUND" ||
        error.code === "QR_TABLE_MISMATCH" ||
        error.code === "QR_TOKEN_INVALID" ||
        error.status === 404
      ) {
        return { status: "invalid" };
      }
    }

    return { status: "error" };
  }
}

export async function validateDineInSession(
  sessionId: string,
  sessionToken: string,
  tableCode: string,
): Promise<ValidateDineInSessionResult> {
  try {
    const session = await api.tables.getSession(sessionId, sessionToken);
    if (session.status !== "Open" || session.isExpired) {
      return { status: "expired" };
    }
    if (session.tableCode !== tableCode) {
      return { status: "invalid" };
    }
    return { status: "open", session };
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 410 || error.code === "TABLE_SESSION_EXPIRED") {
        return { status: "expired" };
      }
      if (
        error.status === 401 ||
        error.status === 403 ||
        error.status === 404 ||
        error.code === "TABLE_SESSION_TOKEN_INVALID" ||
        error.code === "TABLE_SESSION_NOT_FOUND"
      ) {
        return { status: "invalid" };
      }
    }
    return { status: "error" };
  }
}
