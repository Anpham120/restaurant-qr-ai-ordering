import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { createApiClient } from "@cmc/api-client";
import type { AuthUser, LoginRequest, UserRole } from "@cmc/shared-types";

const TOKEN_KEY = "cmc.accessToken";
const USER_KEY = "cmc.currentUser";
export const authStorage = {
  token: () => localStorage.getItem(TOKEN_KEY),
  user: (): AuthUser | null => { try { return JSON.parse(localStorage.getItem(USER_KEY) ?? "null") as AuthUser | null; } catch { return null; } },
  save: (token: string, user: AuthUser) => { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(USER_KEY, JSON.stringify(user)); },
  clear: () => { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); },
};
type AuthContextValue = { user: AuthUser | null; loading: boolean; login: (input: LoginRequest) => Promise<AuthUser>; logout: () => void };
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(authStorage.user());
  const [loading, setLoading] = useState(Boolean(authStorage.token()));
  const api = useMemo(() => createApiClient({ getAccessToken: authStorage.token }), []);
  useEffect(() => { if (!authStorage.token()) return; api.auth.me().then(value => { setUser(value); authStorage.save(authStorage.token()!, value); }).catch(() => { authStorage.clear(); setUser(null); }).finally(() => setLoading(false)); }, [api]);
  const value = useMemo<AuthContextValue>(() => ({ user, loading, login: async input => { const result = await api.auth.login(input); authStorage.save(result.accessToken, result.user); setUser(result.user); return result.user; }, logout: () => { authStorage.clear(); setUser(null); } }), [api, loading, user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used inside AuthProvider"); return value; }
export function ProtectedRoute({ allowedRoles, children }: { allowedRoles: UserRole[]; children: ReactNode }) {
  const { user, loading } = useAuth(); const location = useLocation();
  if (loading) return <div className="cmc-state" role="status">Đang xác minh phiên đăng nhập...</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!allowedRoles.includes(user.role)) return <Navigate to="/unauthorized" replace />;
  return <>{children}</>;
}
