// In-memory mock of every API CONTRACT endpoint. Used when VITE_USE_MOCKS !== "false".
// Force errors with ?mockError=401|403|429|503 in the page URL.
// Preview the "no OCR worker" notice with ?mockOcr=none.
import { camResult, doneFile, members, seed, summary, transactions, usageSeries, type MockDb, type MockUser } from "./data";
import type { AdminTenant, Job } from "../types";

let db: MockDb | null = null;
const getDb = () => (db ??= seed());

const json = (data: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(status === 204 ? null : JSON.stringify(data), { status, headers: { "Content-Type": "application/json", ...headers } });
const err = (status: number, detail: string, headers?: Record<string, string>) => json({ detail }, status, headers);
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Token = "mock.<userId>"
function userFrom(init: RequestInit): MockUser | null {
  const h = (init.headers ?? {}) as Record<string, string>;
  const auth = h["Authorization"] ?? "";
  const id = auth.replace("Bearer mock.", "");
  return getDb().users.find((u) => u.id === id && u.is_active) ?? null;
}

function tick(job: MockDb["jobs"][number]) {
  if (job.status !== "running" && job.status !== "queued") return;
  const started = job.startedAt ?? Date.now();
  const t = (Date.now() - started) / 1000; // seconds
  job.files.forEach((f, i) => {
    const local = t - i * 2;
    if (local <= 0) { f.status = "queued"; f.progress = 0; return; }
    const p = Math.min(100, Math.round((local / 8) * 100));
    if (p >= 100) Object.assign(f, doneFile(f.id, f.name, i));
    else {
      f.status = "running"; f.progress = p;
      f.message = p < 25 ? "waiting for OCR worker" : p < 70 ? "reading pages" : "verifying balances";
    }
  });
  job.progress = Math.round(job.files.reduce((s, f) => s + f.progress, 0) / job.files.length);
  job.status = job.files.every((f) => f.status === "done") ? "done" : "running";
}

const strip = (j: MockDb["jobs"][number]): Job => {
  const { tenant_id: _t, startedAt: _s, ...rest } = j;
  void _t; void _s;
  return rest;
};

export async function mockFetch(url: string, init: RequestInit): Promise<Response> {
  await wait(250 + Math.random() * 250);
  const d = getDb();
  const u = new URL(url, "http://mock.local");
  const path = u.pathname;
  const method = (init.method ?? "GET").toUpperCase();
  const q = u.searchParams;

  if (typeof window !== "undefined") {
    const forced = new URLSearchParams(window.location.search).get("mockError");
    if (forced && !path.startsWith("/api/auth/login") && (path !== "/api/auth/me" || forced === "401")) {
      const code = Number(forced);
      if (code === 429) return err(429, "Too many requests.", { "Retry-After": "30" });
      if (code === 403) return err(403, "You don't have permission to do this.");
      if (code === 401) return err(401, "Session expired.");
      return err(code || 500, "Service temporarily unavailable.");
    }
  }

  const body = () => (typeof init.body === "string" ? JSON.parse(init.body) : {});
  const m = (re: RegExp) => path.match(re);

  // ---------- PUBLIC / AUTH ----------
  const noOcr = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("mockOcr") === "none";
  if (path === "/api/health") return json({ status: "ok", db: "ok", redis: "ok", queues: { cpu: 0, ocr: 1 }, workers: { cpu: 4, ocr: noOcr ? 0 : 1 }, ocr_device: noOcr ? "none" : "cuda:0", ocr_warning: noOcr ? "No OCR worker online" : null });
  if (path === "/api/auth/login" && method === "POST") {
    const p = init.body as URLSearchParams;
    const user = d.users.find((x) => x.email === p.get("username")?.toLowerCase().trim());
    if (!user || user.password !== p.get("password")) return err(401, "Incorrect email or password.");
    user.last_login_at = new Date().toISOString();
    return json({ access_token: `mock.${user.id}`, token_type: "bearer" });
  }
  if (path === "/api/auth/register" && method === "POST") {
    const b = body();
    if (!b.accept_terms) return json({ detail: [{ loc: ["body", "accept_terms"], msg: "You must accept the terms" }] }, 422);
    if (d.users.some((x) => x.email === b.email.toLowerCase())) return err(409, "An account with this email already exists.");
    const tid = `t_${++d.seq}`;
    d.tenants.push({ id: tid, name: b.org_name, plan: "Trial", status: "active", max_files: 3, max_upload_mb: 10, created_at: new Date().toISOString(), retention_hours: 72, monthly_statement_quota: 50 });
    const nu: MockUser = { id: `u_${++d.seq}`, email: b.email.toLowerCase(), password: b.password, role: "owner", is_superuser: false, tenant_id: tid, is_active: true, created_at: new Date().toISOString(), last_login_at: new Date().toISOString() };
    d.users.push(nu);
    return json({ access_token: `mock.${nu.id}`, token_type: "bearer" }, 201);
  }
  const inv = m(/^\/api\/auth\/invite\/([^/]+)$/);
  if (inv && method === "GET") {
    const i = d.invites.find((x) => x.token === inv[1]);
    if (!i) return err(404, "This invite link is invalid or has expired.");
    const t = d.tenants.find((x) => x.id === i.tenant_id)!;
    return json({ email: i.email, org_name: t.name, role: i.role, expires_at: i.expires_at });
  }
  if (path === "/api/auth/accept-invite" && method === "POST") {
    const b = body();
    const i = d.invites.find((x) => x.token === b.token);
    if (!i) return err(404, "This invite link is invalid or has expired.");
    const nu: MockUser = { id: `u_${++d.seq}`, email: i.email, password: b.password, role: i.role, is_superuser: false, tenant_id: i.tenant_id, is_active: true, created_at: new Date().toISOString(), last_login_at: new Date().toISOString() };
    d.users.push(nu);
    d.invites = d.invites.filter((x) => x !== i);
    return json({ access_token: `mock.${nu.id}`, token_type: "bearer" });
  }

  // ---------- AUTHENTICATED ----------
  const user = userFrom(init);
  if (!user) return err(401, "Not authenticated.");
  const tenant = d.tenants.find((t) => t.id === user.tenant_id)!;
  const isAdmin = user.role === "owner" || user.role === "admin";
  const forbid = () => err(403, "You don't have permission to do this.");

  if (path === "/api/auth/me") return json({ id: user.id, email: user.email, role: user.role, is_superuser: user.is_superuser, tenant_id: tenant.id, org_name: tenant.name, org_status: tenant.status, plan: tenant.plan });
  if (path === "/api/auth/change-password" && method === "POST") {
    const b = body();
    if (b.current_password !== user.password) return err(400, "Current password is incorrect.");
    user.password = b.new_password;
    return json(null, 204);
  }

  // Jobs
  const myJobs = () => d.jobs.filter((j) => j.tenant_id === tenant.id);
  if (path === "/api/v1/jobs" && method === "GET") {
    myJobs().forEach(tick);
    const all = [...myJobs()].sort((a, b) => b.created.localeCompare(a.created));
    const off = Number(q.get("offset") ?? 0), lim = Number(q.get("limit") ?? 20);
    return json({ items: all.slice(off, off + lim).map(strip), total: all.length });
  }
  if (path === "/api/v1/jobs" && method === "POST") {
    if (tenant.status === "suspended") return forbid();
    const fd = init.body as FormData;
    const files = fd.getAll("files[]") as File[];
    if (!files.length) return err(400, "Add at least one PDF.");
    if (files.some((f) => !f.name.toLowerCase().endsWith(".pdf"))) return err(400, "Only PDF files are accepted.");
    if (files.length > tenant.max_files) return err(400, `Your plan allows up to ${tenant.max_files} files per job.`);
    if (files.some((f) => f.size > tenant.max_upload_mb * 1024 * 1024)) return err(400, `Each file must be under ${tenant.max_upload_mb} MB.`);
    if (fd.get("password") === "wrong") return err(400, "The PDF password is incorrect.");
    const job = {
      id: `job_${(++d.seq).toString(36)}`, tenant_id: tenant.id, status: "queued" as const, created: new Date().toISOString(),
      use_ocr: fd.get("use_ocr") !== "false", dpi: Number(fd.get("dpi") ?? 300) as 300, bank: (fd.get("bank") as string) || null, progress: 0, startedAt: Date.now(),
      files: files.map((f, i) => ({ id: `f${i + 1}`, name: f.name, status: "queued" as const, progress: 0, message: "queued", error: null, result: null })),
    };
    d.jobs.push(job);
    return json({ job_id: job.id, files: job.files }, 201);
  }
  const jm = m(/^\/api\/v1\/jobs\/([^/]+)(?:\/files\/(\d+)\/(result|transactions|download))?$/);
  if (jm) {
    const job = myJobs().find((j) => j.id === jm[1]);
    if (!job) return err(404, "Job not found.");
    tick(job);
    if (!jm[2]) return json(strip(job));
    const idx = Number(jm[2]);
    const f = job.files[idx];
    if (!f) return err(404, "File not found.");
    if (f.status !== "done" || !f.result) return err(409, "This statement is still being processed.");
    if (jm[3] === "result") return json(camResult(f.result, idx + d.jobs.indexOf(job)));
    if (jm[3] === "transactions") {
      const off = Number(q.get("offset") ?? 0), lim = Number(q.get("limit") ?? 100);
      const flagged = camResult(f.result, idx).validation.flagged_rows.map((r) => r.row);
      return json({ items: transactions(f.result.rows, flagged, off, lim), total: f.result.rows });
    }
    return new Response(new Blob(["Mock Excel export for " + f.name], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), { status: 200 });
  }

  // API keys
  if (path === "/api/v1/api-keys") {
    if (!isAdmin) return forbid();
    if (method === "GET") return json(d.keys.filter((k) => k.tenant_id === tenant.id).map(({ tenant_id: _t, ...k }) => k));
    if (method === "POST") {
      const b = body();
      const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
      const rand = Array.from({ length: 40 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
      const k = { id: `k${++d.seq}`, tenant_id: tenant.id, name: b.name, prefix: `icam_live_${rand.slice(0, 4)}`, scopes: b.scopes, created_at: new Date().toISOString(), created_by: user.email, last_used_at: null, revoked_at: null, requests_30d: 0 };
      d.keys.push(k);
      const { tenant_id: _t, ...pub } = k;
      void _t;
      return json({ ...pub, secret: `icam_live_${rand}` }, 201);
    }
  }
  const km = m(/^\/api\/v1\/api-keys\/([^/]+)$/);
  if (km && method === "DELETE") {
    if (!isAdmin) return forbid();
    const k = d.keys.find((x) => x.id === km[1] && x.tenant_id === tenant.id);
    if (!k) return err(404, "Key not found.");
    k.revoked_at = new Date().toISOString();
    return json(null, 204);
  }

  // Usage
  if (path === "/api/v1/usage") {
    const by = q.get("group_by") ?? "day";
    const fromD = q.get("from"), toD = q.get("to");
    const days = fromD && toD ? Math.max(1, Math.min(366, Math.round((Date.parse(toD) - Date.parse(fromD)) / 86400000) + 1)) : 30;
    const f = days / 30;
    let series = usageSeries(days);
    if (by === "api_key") series = [{ key: "k1", label: "LOS production", statements: Math.round(612 * f), pages: Math.round(7300 * f) }, { key: "portal", label: "Portal uploads", statements: Math.round(210 * f), pages: Math.round(2100 * f) }];
    if (by === "user") series = members(d, tenant.id).map((mm, i) => ({ key: mm.id, label: mm.email, statements: Math.max(0, Math.round((300 - i * 120) * f)), pages: Math.max(0, Math.round((3000 - i * 1100) * f)) }));
    const totals = series.reduce((a, s) => ({ statements: a.statements + s.statements, pages: a.pages + s.pages }), { statements: 0, pages: 0 });
    return json({ plan: { name: tenant.plan, max_files_per_job: tenant.max_files, max_upload_mb: tenant.max_upload_mb, monthly_statement_quota: tenant.monthly_statement_quota }, totals, series });
  }

  // Org
  if (path === "/api/v1/org") {
    const { monthly_statement_quota: _m, ...org } = tenant;
    void _m;
    if (method === "GET") return json(org);
    if (method === "PATCH") { if (!isAdmin) return forbid(); tenant.name = body().name; return json({ ...org, name: tenant.name }); }
  }
  if (path === "/api/v1/org/members" && method === "GET") return json(members(d, tenant.id));
  const mm = m(/^\/api\/v1\/org\/members\/([^/]+)$/);
  if (mm) {
    if (!isAdmin) return forbid();
    const target = d.users.find((x) => x.id === mm[1] && x.tenant_id === tenant.id);
    if (!target) return err(404, "Member not found.");
    if (target.role === "owner") return err(400, "The owner can't be changed or removed.");
    if (method === "PATCH") { Object.assign(target, body()); return json(members(d, tenant.id).find((x) => x.id === target.id)); }
    if (method === "DELETE") { d.users = d.users.filter((x) => x !== target); return json(null, 204); }
  }
  if (path === "/api/v1/org/invites") {
    if (!isAdmin) return forbid();
    if (method === "GET") return json(d.invites.filter((i) => i.tenant_id === tenant.id).map(({ tenant_id: _t, token: _k, ...i }) => i));
    if (method === "POST") {
      const b = body();
      const token = `inv-${(++d.seq).toString(36)}`;
      const i = { id: `inv${d.seq}`, tenant_id: tenant.id, email: b.email, role: b.role, created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 7 * 86400000).toISOString(), token };
      d.invites.push(i);
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      return json({ id: i.id, invite_url: `${origin}/invite/${token}`, expires_at: i.expires_at }, 201);
    }
  }
  const im = m(/^\/api\/v1\/org\/invites\/([^/]+)$/);
  if (im && method === "DELETE") { if (!isAdmin) return forbid(); d.invites = d.invites.filter((x) => x.id !== im[1]); return json(null, 204); }

  // Super-admin
  if (path.startsWith("/api/v1/admin")) {
    if (!user.is_superuser) return forbid();
    if (path === "/api/v1/admin/overview") return json({ tenants: d.otherTenants.length, active_tenants_30d: 4, statements_30d: 2860, pages_30d: 31200, queue: { cpu: 2, ocr: 5 }, workers: { cpu: 4, ocr: noOcr ? 0 : 1 }, ocr_device: noOcr ? "none" : "cuda:0" });
    if (path === "/api/v1/admin/tenants") {
      const query = (q.get("query") ?? "").toLowerCase(), status = q.get("status");
      const items = d.otherTenants.filter((t) => t.name.toLowerCase().includes(query) && (!status || t.status === status));
      const lim = Number(q.get("limit") ?? 50), off = Number(q.get("offset") ?? 0);
      return json({ items: items.slice(off, off + lim), total: items.length });
    }
    const tm = m(/^\/api\/v1\/admin\/tenants\/([^/]+)$/);
    if (tm) {
      const t = d.otherTenants.find((x) => x.id === tm[1]);
      if (!t) return err(404, "Tenant not found.");
      const lim = (t as unknown as { _lim?: { max_files: number; max_upload_mb: number; monthly_statement_quota: number | null } })._lim ??= { max_files: 5, max_upload_mb: 25, monthly_statement_quota: 2000 };
      if (method === "PATCH") {
        const b = body();
        for (const k of ["plan", "status", "name"] as const) if (b[k] !== undefined) (t as unknown as Record<string, unknown>)[k] = b[k];
        for (const k of ["max_files", "max_upload_mb", "monthly_statement_quota"] as const) if (b[k] !== undefined) lim[k] = b[k];
        if (t.id === tenant.id) { if (b.status) tenant.status = b.status; if (b.plan) tenant.plan = b.plan; Object.assign(tenant, lim); }
        const { _lim: _l, ...pub } = t as AdminTenant & { _lim?: unknown };
        return json(pub);
      }
      const { _lim: _l2, ...pub } = t as AdminTenant & { _lim?: unknown };
      return json({ ...pub, ...lim, members: t.id === tenant.id ? members(d, tenant.id) : [], usage: usageSeries(30, t.users), api_keys: t.id === tenant.id ? d.keys.map(({ tenant_id: _x, ...k }) => k) : [] });
    }
    const rk = m(/^\/api\/v1\/admin\/api-keys\/([^/]+)\/revoke$/);
    if (rk) { const k = d.keys.find((x) => x.id === rk[1]); if (k) k.revoked_at = new Date().toISOString(); return json(null, 204); }
  }

  void summary;
  return err(404, "Not found.");
}
