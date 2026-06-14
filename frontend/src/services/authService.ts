import { getApiBaseUrl } from "./apiClient";

export type UserRole = "Customer" | "Staff" | "Kitchen" | "Admin";

export type AuthUser = {
  userId: string;
  fullName: string;
  email: string;
  role: UserRole;
};

type LoginResponse = {
  accessToken: string;
  expiresAt: string;
  user: AuthUser;
};

type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
  };
};

const authStorageKey = "cmc.auth";
const accessTokenStorageKey = "cmc.accessToken";

export async function login(email: string, password: string): Promise<AuthUser> {
  const response = await fetch(`${getApiBaseUrl()}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  const payload = (await response.json().catch(() => ({}))) as LoginResponse & ApiErrorPayload;
  if (!response.ok) {
    throw new Error(payload.error?.message ?? "Không thể đăng nhập.");
  }

  storeAuth(payload);
  return payload.user;
}

export function storeAuth(auth: LoginResponse) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(authStorageKey, JSON.stringify(auth));
  window.localStorage.setItem(accessTokenStorageKey, auth.accessToken);
}

export function getStoredAuth(): LoginResponse | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(authStorageKey);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as LoginResponse;
  } catch {
    logout();
    return null;
  }
}

export function getStoredUser(): AuthUser | null {
  return getStoredAuth()?.user ?? null;
}

export function getStoredAccessToken() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(accessTokenStorageKey);
}

export function getAuthHeaders(): Record<string, string> {
  const token = getStoredAccessToken();

  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function logout() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(authStorageKey);
  window.localStorage.removeItem(accessTokenStorageKey);
}

export function hasAllowedRole(user: AuthUser | null, roles: UserRole[]) {
  return Boolean(user && roles.includes(user.role));
}
