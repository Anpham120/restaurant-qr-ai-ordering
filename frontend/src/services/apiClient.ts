import { createApiClient } from "@cmc/api-client";
import { authStorage } from "@cmc/auth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "https://localhost:7296/api";

export const api = createApiClient({
  baseUrl: apiBaseUrl,
  getAccessToken: authStorage.token,
  onUnauthorized: authStorage.clear,
});

export function getApiBaseUrl() {
  return apiBaseUrl;
}
