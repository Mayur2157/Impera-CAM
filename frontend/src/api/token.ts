// The JWT lives in memory and sessionStorage (closing the tab signs out), never
// localStorage, which outlives the session and is readable by any script on the origin.
const KEY = "icam.token";
let memory: string | null = null;

export function getToken(): string | null {
  if (memory) return memory;
  try {
    memory = sessionStorage.getItem(KEY);
  } catch {
    /* storage blocked: memory only */
  }
  return memory;
}

export function setToken(token: string | null): void {
  memory = token;
  try {
    if (token) sessionStorage.setItem(KEY, token);
    else sessionStorage.removeItem(KEY);
  } catch {
    /* storage blocked: memory only */
  }
}
