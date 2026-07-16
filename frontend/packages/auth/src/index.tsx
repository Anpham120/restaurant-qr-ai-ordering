import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { createApiClient } from "@cmc/api-client";
import type { AuthUser, LoginRequest, UserRole } from "@cmc/shared-types";

const TOKEN_KEY = "cmc.accessToken";
const USER_KEY = "cmc.currentUser";
const AUTH_CHANGED_EVENT = "cmc:auth-changed";

function notifyAuthChanged() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
  }
}

export const authStorage = {
  token: () => sessionStorage.getItem(TOKEN_KEY),
  save: (token: string) => {
    sessionStorage.setItem(TOKEN_KEY, token);
    localStorage.removeItem(USER_KEY);
    notifyAuthChanged();
  },
  clear: () => {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    notifyAuthChanged();
  },
};

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  login: (input: LoginRequest) => Promise<AuthUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(Boolean(authStorage.token()));
  const api = useMemo(() => createApiClient({ getAccessToken: authStorage.token }), []);

  useEffect(() => {
    let verification = 0;
    const syncSession = () => {
      const token = authStorage.token();
      if (!token) {
        verification += 1;
        setUser(null);
        setLoading(false);
        return;
      }

      const currentVerification = ++verification;
      setLoading(true);
      api.auth
        .me()
        .then((value) => {
          if (currentVerification === verification) setUser(value);
        })
        .catch(() => {
          if (currentVerification !== verification) return;
          authStorage.clear();
          setUser(null);
        })
        .finally(() => {
          if (currentVerification === verification) setLoading(false);
        });
    };

    syncSession();
    window.addEventListener(AUTH_CHANGED_EVENT, syncSession);
    window.addEventListener("storage", syncSession);
    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, syncSession);
      window.removeEventListener("storage", syncSession);
    };
  }, [api]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (input) => {
        const result = await api.auth.login(input);
        authStorage.save(result.accessToken);
        setUser(result.user);
        return result.user;
      },
      logout: () => {
        authStorage.clear();
        setUser(null);
      },
    }),
    [api, loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}

export function ProtectedRoute({
  allowedRoles,
  children,
}: {
  allowedRoles: UserRole[];
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="cmc-state" role="status">
        Đang xác minh phiên đăng nhập...
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (!allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }
  return <>{children}</>;
}
