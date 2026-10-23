import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { request, setUnauthorizedHandler } from "@/api/client";
import { keys, useMe } from "@/api/hooks";
import { getToken, setToken } from "@/api/token";
import type { Me } from "@/api/types";

type AuthStatus = "loading" | "signed-in" | "signed-out" | "error";

interface AuthContextValue {
  status: AuthStatus;
  me: Me | undefined;
  error: unknown;
  retry: () => void;
  /** Store a fresh token and load the account; resolves once /me answered. */
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const me = useMe(!!token);

  const signOut = useCallback(() => {
    setToken(null);
    setTokenState(null);
    queryClient.clear();
  }, [queryClient]);

  const signIn = useCallback(
    async (next: string) => {
      setToken(next);
      try {
        await queryClient.fetchQuery({ queryKey: keys.me, queryFn: () => request<Me>("/api/auth/me") });
      } catch (e) {
        setToken(null); // never keep a token whose account couldn't be loaded
        throw e;
      }
      setTokenState(next);
    },
    [queryClient],
  );

  // any 401 from an authenticated call means the session ended (expired, user removed)
  useEffect(() => {
    setUnauthorizedHandler(signOut);
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  const value = useMemo<AuthContextValue>(() => {
    let status: AuthStatus = "signed-out";
    if (token) status = me.data ? "signed-in" : me.isError ? "error" : "loading";
    return { status, me: me.data, error: me.error, retry: () => void me.refetch(), signIn, signOut };
  }, [token, me, signIn, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
