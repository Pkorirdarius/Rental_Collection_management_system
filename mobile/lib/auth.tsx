import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, clearTokens, loadTokens, saveTokens, setAuthToken } from "./api";
import type { AuthSession, User } from "./types";

interface LoginOutcome {
  mfaRequired: boolean;
  challenge?: string;
  role?: User["role"];
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<LoginOutcome>;
  verify2fa: (challenge: string, code: string) => Promise<User["role"]>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const persist = useCallback(async (session: AuthSession) => {
    await saveTokens(session.access, session.refresh);
    setAuthToken(session.access);
    setUser(session.user);
  }, []);

  const refreshUser = useCallback(async () => {
    const { data } = await api.get<User>("/auth/me");
    setUser(data);
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { access, refresh } = await loadTokens();
        if (!access && !refresh) return;
        if (access) setAuthToken(access);
        const { data } = await api.get<User>("/auth/me");
        if (mounted) setUser(data);
      } catch {
        await clearTokens();
        setAuthToken(null);
        if (mounted) setUser(null);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(
    async (identifier: string, password: string): Promise<LoginOutcome> => {
      const { data } = await api.post<AuthSession | { mfa_required: true; challenge: string }>(
        "/auth/login",
        { identifier, password },
      );
      if ("mfa_required" in data) {
        return { mfaRequired: true, challenge: data.challenge };
      }
      await persist(data);
      return { mfaRequired: false, role: data.user.role };
    },
    [persist],
  );

  const verify2fa = useCallback(
    async (challenge: string, code: string) => {
      const { data } = await api.post<AuthSession>("/auth/2fa/verify", { challenge, code });
      await persist(data);
      return data.user.role;
    },
    [persist],
  );

  const logout = useCallback(async () => {
    try {
      const { refresh } = await loadTokens();
      if (refresh) await api.post("/auth/logout", { refresh });
    } catch {
      // Local sign-out should always succeed.
    } finally {
      await clearTokens();
      setAuthToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, verify2fa, logout, refreshUser }),
    [user, loading, login, verify2fa, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
