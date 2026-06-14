import { createApiClient } from "@cmc/api-client";
import type { AuthUser, RegisterRequest } from "@cmc/shared-types";

const api = createApiClient({
  getAccessToken: () =>
    typeof window === "undefined" ? null : window.localStorage.getItem("cmc.accessToken"),
});

export async function registerUser(payload: RegisterRequest): Promise<AuthUser> {
  return api.auth.register(payload);
}
