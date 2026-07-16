const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "https://localhost:7296/api";

export function getApiBaseUrl() {
  return apiBaseUrl;
}

