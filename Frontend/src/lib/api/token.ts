// Token kept in memory + sessionStorage (never localStorage).
const KEY = "icam.token";
let memory: string | null = null;
const listeners = new Set<() => void>();

export function getToken(): string | null {
  if (memory) return memory;
  if (typeof window === "undefined") return null;
  memory = window.sessionStorage.getItem(KEY);
  return memory;
}

export function setToken(t: string | null) {
  memory = t;
  if (typeof window !== "undefined") {
    if (t) window.sessionStorage.setItem(KEY, t);
    else window.sessionStorage.removeItem(KEY);
  }
  listeners.forEach((l) => l());
}

export function onTokenChange(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
