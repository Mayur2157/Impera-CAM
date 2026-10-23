import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type * as T from "./types";

const k = {
  me: ["me"] as const,
  jobs: (limit: number, offset: number) => ["jobs", limit, offset] as const,
  job: (id: string) => ["job", id] as const,
  result: (id: string, i: number) => ["result", id, i] as const,
  txns: (id: string, i: number, o: number, l: number) => ["txns", id, i, o, l] as const,
  keys: ["api-keys"] as const,
  usage: (p: UsageParams) => ["usage", p] as const,
  org: ["org"] as const,
  members: ["members"] as const,
  invites: ["invites"] as const,
  admin: ["admin"] as const,
};

// AUTH
export const meQuery = () => queryOptions({ queryKey: k.me, queryFn: () => api<T.Me>("/api/auth/me"), retry: false, staleTime: 60_000 });
export const useMe = (enabled = true) => useQuery({ ...meQuery(), enabled });
export const login = (email: string, password: string) =>
  api<T.TokenResponse>("/api/auth/login", { method: "POST", body: new URLSearchParams({ username: email, password }), auth: false });
export const register = (b: T.RegisterRequest) => api<T.TokenResponse>("/api/auth/register", { method: "POST", body: { ...b }, auth: false });
export const useChangePassword = () => useMutation({ mutationFn: (b: T.ChangePasswordRequest) => api<void>("/api/auth/change-password", { method: "POST", body: { ...b } }) });
export const acceptInvite = (b: T.AcceptInviteRequest) => api<T.TokenResponse>("/api/auth/accept-invite", { method: "POST", body: { ...b }, auth: false });
export const useInviteInfo = (token: string) =>
  useQuery({ queryKey: ["invite", token], queryFn: () => api<T.InviteInfo>(`/api/auth/invite/${token}`, { auth: false }), retry: false });

// JOBS
export const useJobs = (limit = 20, offset = 0) => useQuery({ queryKey: k.jobs(limit, offset), queryFn: () => api<T.Paged<T.JobSummary>>("/api/v1/jobs", { query: { limit, offset } }) });
export const useJob = (id: string, refetchInterval: number | false = false) =>
  useQuery({ queryKey: k.job(id), queryFn: () => api<T.Job>(`/api/v1/jobs/${id}`), refetchInterval });
export const useCreateJob = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ fd, onProgress }: { fd: FormData; onProgress?: (pct: number) => void }) =>
      api<T.CreateJobResponse>("/api/v1/jobs", { method: "POST", body: fd, onUploadProgress: onProgress ?? (() => {}) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
};
export const useCamResult = (id: string, i: number) => useQuery({ queryKey: k.result(id, i), queryFn: () => api<T.CamResult>(`/api/v1/jobs/${id}/files/${i}/result`), retry: false });
export const useTransactions = (id: string, i: number, offset = 0, limit = 100) =>
  useQuery({ queryKey: k.txns(id, i, offset, limit), queryFn: () => api<T.Paged<T.Txn>>(`/api/v1/jobs/${id}/files/${i}/transactions`, { query: { offset, limit } }) });
export const downloadExcel = (id: string, i: number) => api<Blob>(`/api/v1/jobs/${id}/files/${i}/download`, { as: "blob" });

// API KEYS
export const useApiKeys = (enabled = true) => useQuery({ queryKey: k.keys, queryFn: () => api<T.ApiKey[]>("/api/v1/api-keys"), enabled });
export const useCreateApiKey = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (b: { name: string; scopes: T.Scope[] }) => api<T.CreatedApiKey>("/api/v1/api-keys", { method: "POST", body: b }), onSuccess: () => qc.invalidateQueries({ queryKey: k.keys }) });
};
export const useRevokeApiKey = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => api<void>(`/api/v1/api-keys/${id}`, { method: "DELETE" }), onSuccess: () => qc.invalidateQueries({ queryKey: k.keys }) });
};

// USAGE
export interface UsageParams { from: string; to: string; group_by: "day" | "api_key" | "user" }
export const useUsage = (p: UsageParams) => useQuery({ queryKey: k.usage(p), queryFn: () => api<T.Usage>("/api/v1/usage", { query: { ...p } }) });

// ORG
export const useOrg = () => useQuery({ queryKey: k.org, queryFn: () => api<T.Org>("/api/v1/org") });
export const useUpdateOrg = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (b: { name: string }) => api<T.Org>("/api/v1/org", { method: "PATCH", body: b }), onSuccess: () => { qc.invalidateQueries({ queryKey: k.org }); qc.invalidateQueries({ queryKey: k.me }); } });
};
export const useMembers = () => useQuery({ queryKey: k.members, queryFn: () => api<T.Member[]>("/api/v1/org/members") });
export const useUpdateMember = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, ...b }: { id: string; role?: T.Role; is_active?: boolean }) => api<T.Member>(`/api/v1/org/members/${id}`, { method: "PATCH", body: b }), onSuccess: () => qc.invalidateQueries({ queryKey: k.members }) });
};
export const useRemoveMember = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => api<void>(`/api/v1/org/members/${id}`, { method: "DELETE" }), onSuccess: () => qc.invalidateQueries({ queryKey: k.members }) });
};
export const useInvites = (enabled = true) => useQuery({ queryKey: k.invites, queryFn: () => api<T.Invite[]>("/api/v1/org/invites"), enabled });
export const useCreateInvite = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (b: { email: string; role: "admin" | "member" }) => api<T.CreatedInvite>("/api/v1/org/invites", { method: "POST", body: b }), onSuccess: () => qc.invalidateQueries({ queryKey: k.invites }) });
};
export const useDeleteInvite = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => api<void>(`/api/v1/org/invites/${id}`, { method: "DELETE" }), onSuccess: () => qc.invalidateQueries({ queryKey: k.invites }) });
};

// SUPER-ADMIN
export const useAdminOverview = () => useQuery({ queryKey: [...k.admin, "overview"], queryFn: () => api<T.AdminOverview>("/api/v1/admin/overview") });
export const useAdminTenants = (p: { query?: string; status?: string; limit?: number; offset?: number }) =>
  useQuery({ queryKey: [...k.admin, "tenants", p], queryFn: () => api<T.Paged<T.AdminTenant>>("/api/v1/admin/tenants", { query: { limit: 50, offset: 0, ...p } }) });
export const useAdminTenant = (id: string) => useQuery({ queryKey: [...k.admin, "tenant", id], queryFn: () => api<T.AdminTenantDetail>(`/api/v1/admin/tenants/${id}`) });
export const useUpdateAdminTenant = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, ...b }: T.AdminTenantPatch & { id: string }) => api<T.AdminTenant>(`/api/v1/admin/tenants/${id}`, { method: "PATCH", body: b }), onSuccess: () => qc.invalidateQueries({ queryKey: k.admin }) });
};
export const useAdminRevokeKey = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => api<void>(`/api/v1/admin/api-keys/${id}/revoke`, { method: "POST" }), onSuccess: () => qc.invalidateQueries({ queryKey: k.admin }) });
};

// PUBLIC
export const useHealth = () => useQuery({ queryKey: ["health"], queryFn: () => api<T.Health>("/api/health", { auth: false }) });
