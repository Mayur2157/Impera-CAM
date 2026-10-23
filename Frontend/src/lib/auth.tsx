import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getToken, onTokenChange, setToken } from "./api/token";
import { useMe } from "./api/hooks";
import type { Me } from "./api/types";

interface AuthCtx {
  ready: boolean;
  token: string | null;
  me: Me | undefined;
  meLoading: boolean;
  isAdmin: boolean;
  signIn: (token: string) => void;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [ready, setReady] = useState(false);
  const [token, setTok] = useState<string | null>(null);

  useEffect(() => {
    setTok(getToken());
    setReady(true);
    const off = onTokenChange(() => setTok(getToken()));
    return () => { off(); };
  }, []);

  const me = useMe(ready && !!token);

  const value: AuthCtx = {
    ready,
    token,
    me: token ? me.data : undefined,
    meLoading: !!token && me.isLoading,
    isAdmin: me.data?.role === "owner" || me.data?.role === "admin",
    signIn: (t) => {
      qc.clear();
      setToken(t);
    },
    signOut: async () => {
      await qc.cancelQueries();
      qc.clear();
      setToken(null);
    },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}

/** Only allow same-site relative redirects. */
export function safeNext(next: unknown): string {
  return typeof next === "string" && next.startsWith("/") && !next.startsWith("//") ? next : "/app";
}
