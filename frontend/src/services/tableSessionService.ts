import { ApiError, createApiClient } from "@cmc/api-client";

const api = createApiClient();

type TableSession = Awaited<ReturnType<typeof api.tables.openSession>>;

export type OpenDineInSessionResult =
  | { status: "open"; session: TableSession }
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
