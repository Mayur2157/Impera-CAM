// The only module that talks to the network. Same origin in every environment:
// Vite proxies /api in development and FastAPI serves the build in production.
import { getToken } from "./token";

export class ApiError extends Error {
  readonly status: number;
  readonly retryAfter: number | null;
  /** Field-level messages from a 422, keyed by field name. */
  readonly fields: Record<string, string>;

  constructor(status: number, message: string, retryAfter: number | null = null, fields = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfter = retryAfter;
    this.fields = fields;
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  query?: Query;
  json?: unknown;
  form?: URLSearchParams;
  /** false for sign-in/sign-up: a 401 there is a wrong password, not an expired session */
  auth?: boolean;
  signal?: AbortSignal;
}

let onUnauthorized: (() => void) | null = null;

/** The auth provider registers how to react to an expired or revoked session. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

const NETWORK_MESSAGE = "Can't reach Impera CAM — check your connection and try again.";

export function url(path: string, query?: Query): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `${path}?${s}` : path;
}

interface ValidationItem {
  loc?: (string | number)[];
  msg: string;
}

/** Turn FastAPI's error body into one readable message, plus per-field messages. */
export function parseError(status: number, body: unknown, retryAfterHeader: string | null): ApiError {
  const retryAfter = retryAfterHeader ? Number(retryAfterHeader) || null : null;
  const detail = (body as { detail?: unknown } | null)?.detail;
  let message = `The request failed (error ${status}). Try again in a moment.`;
  const fields: Record<string, string> = {};

  if (typeof detail === "string") {
    message = detail.charAt(0).toUpperCase() + detail.slice(1);
  } else if (Array.isArray(detail)) {
    const items = detail as ValidationItem[];
    for (const d of items) {
      const field = String(d.loc?.[d.loc.length - 1] ?? "");
      // pydantic prefixes custom messages with "Value error, "
      if (field && !fields[field]) fields[field] = d.msg.replace(/^Value error, /, "");
    }
    message = Object.values(fields)[0] ?? "Some fields need attention.";
  }
  if (status === 429 && retryAfter) message = `${message.replace(/\.$/, "")}. Try again in ${retryAfter} s.`;
  return new ApiError(status, message, retryAfter, fields);
}

function headers(auth: boolean): Record<string, string> {
  const token = auth ? getToken() : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function handle401(status: number, auth: boolean) {
  if (status === 401 && auth) onUnauthorized?.();
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const auth = opts.auth ?? true;
  const h = headers(auth);
  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    h["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  } else if (opts.form) {
    body = opts.form;
  }
  let res: Response;
  try {
    res = await fetch(url(path, opts.query), {
      method: opts.method ?? (body ? "POST" : "GET"),
      headers: h,
      body,
      signal: opts.signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, NETWORK_MESSAGE);
  }
  if (!res.ok) {
    handle401(res.status, auth);
    const data = await res.json().catch(() => null);
    throw parseError(res.status, data, res.headers.get("Retry-After"));
  }
  return res;
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(path, opts);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** A file response, with the server's filename when it sends one. */
export async function requestBlob(
  path: string,
  opts: RequestOptions = {},
): Promise<{ blob: Blob; filename: string | null }> {
  const res = await send(path, opts);
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const m = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(disposition);
  const filename = m ? decodeURIComponent(m[1] ?? m[2] ?? "") : null;
  return { blob: await res.blob(), filename };
}

/** Multipart upload with progress (fetch cannot report upload progress). */
export function upload<T>(
  path: string,
  form: FormData,
  onProgress?: (percent: number) => void,
  signal?: AbortSignal,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", path);
    for (const [k, v] of Object.entries(headers(true))) xhr.setRequestHeader(k, v);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((100 * e.loaded) / e.total));
    };
    xhr.onload = () => {
      let data: unknown = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        /* non-JSON body */
      }
      if (xhr.status >= 200 && xhr.status < 300) return resolve(data as T);
      handle401(xhr.status, true);
      reject(parseError(xhr.status, data, xhr.getResponseHeader("Retry-After")));
    };
    xhr.onerror = () => reject(new ApiError(0, NETWORK_MESSAGE));
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort());
    xhr.send(form);
  });
}
