import { getToken, setToken } from "./token";

export class ApiError extends Error {
  status: number;
  retryAfter: number | null;
  constructor(status: number, message: string, retryAfter: number | null = null) {
    super(message);
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export const USE_MOCKS = (import.meta.env["VITE_USE_MOCKS"] ?? "true") !== "false";
const BASE = ((import.meta.env["VITE_API_BASE_URL"] as string | undefined) ?? "").replace(/\/$/, "");

// Mock server is loaded only in mock mode, so real-backend builds don't ship demo data.
const mockFetch = async (url: string, init: RequestInit) => (await import("./mocks/server")).mockFetch(url, init);

type Body = Record<string, unknown> | FormData | URLSearchParams | undefined;

export interface RequestOpts {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: Body;
  query?: Record<string, string | number | boolean | undefined | null>;
  as?: "json" | "blob";
  /** Upload progress 0-100 (multipart bodies) */
  onUploadProgress?: ((pct: number) => void) | undefined;
  auth?: boolean;
}

function buildUrl(path: string, query?: RequestOpts["query"]) {
  const qs = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  const s = qs.toString();
  return `${BASE}${path}${s ? `?${s}` : ""}`;
}

async function normalizeError(res: Response): Promise<ApiError> {
  const ra = res.headers.get("Retry-After");
  const retryAfter = ra ? Number(ra) : null;
  let message = `Request failed (${res.status})`;
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") message = data.detail;
    else if (Array.isArray(data?.detail))
      message = data.detail.map((d: { loc?: unknown[]; msg: string }) => `${(d.loc ?? []).slice(1).join(".") || "field"}: ${d.msg}`).join("; ");
  } catch {
    /* non-JSON */
  }
  if (res.status === 429 && retryAfter) message = `${message} Please wait ${retryAfter} s and try again.`;
  return new ApiError(res.status, message, retryAfter);
}

export function redirectToLogin() {
  if (typeof window === "undefined") return;
  const here = window.location.pathname + window.location.search;
  if (window.location.pathname.startsWith("/login")) return;
  window.location.assign(`/login?next=${encodeURIComponent(here)}`);
}

export async function api<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const { method = "GET", body, query, as = "json", auth = true, onUploadProgress } = opts;
  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;
  if (body instanceof FormData || body instanceof URLSearchParams) payload = body;
  else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const token = getToken();
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;

  const url = buildUrl(path, query);
  const init: RequestInit = { method, headers, body: payload ?? null };
  let res: Response;
  try {
    if (onUploadProgress && USE_MOCKS) {
      for (let p = 0; p <= 100; p += 20) { onUploadProgress(p); await new Promise((r) => setTimeout(r, 120)); }
      res = await mockFetch(url, init);
    } else if (onUploadProgress) res = await xhrFetch(url, method, headers, payload, onUploadProgress);
    else res = USE_MOCKS ? await mockFetch(url, init) : await fetch(url, init);
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }

  if (!res.ok) {
    const err = await normalizeError(res);
    if (res.status === 401 && auth && token) {
      setToken(null);
      redirectToLogin();
    }
    throw err;
  }
  if (res.status === 204) return undefined as T;
  if (as === "blob") return (await res.blob()) as T;
  return (await res.json()) as T;
}

export function errorMessage(e: unknown) {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Something went wrong.";
}

/** fetch() can't report upload progress; XHR can. Returns a standard Response. */
function xhrFetch(url: string, method: string, headers: Record<string, string>, body: BodyInit | undefined, onProgress: (pct: number) => void) {
  return new Promise<Response>((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open(method, url);
    Object.entries(headers).forEach(([k, v]) => x.setRequestHeader(k, v));
    x.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100)); };
    x.onload = () => {
      const h = new Headers();
      x.getAllResponseHeaders().trim().split(/\r?\n/).forEach((line) => { const i = line.indexOf(":"); if (i > 0) h.set(line.slice(0, i).trim(), line.slice(i + 1).trim()); });
      resolve(new Response(x.status === 204 ? null : x.responseText, { status: x.status, headers: h }));
    };
    x.onerror = () => reject(new Error("network"));
    x.send((body as XMLHttpRequestBodyInit | undefined) ?? null);
  });
}
