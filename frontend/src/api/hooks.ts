import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { request } from "./client";
import type { Health, Job, Me, Page, UsageReport } from "./types";

export const keys = {
  me: ["me"] as const,
  jobs: (limit: number, offset: number) => ["jobs", limit, offset] as const,
  job: (id: string) => ["job", id] as const,
  usage: (params: Record<string, string>) => ["usage", params] as const,
  health: ["health"] as const,
};

export function useMe(enabled: boolean) {
  return useQuery({
    queryKey: keys.me,
    queryFn: ({ signal }) => request<Me>("/api/auth/me", { signal }),
    enabled,
    staleTime: 60_000,
    retry: false,
  });
}

const active = (j: Job | undefined) => !!j && (j.status === "queued" || j.status === "running");

export function useJobs(limit: number, offset: number) {
  return useQuery({
    queryKey: keys.jobs(limit, offset),
    queryFn: ({ signal }) => request<Page<Job>>("/api/v1/jobs", { query: { limit, offset }, signal }),
    placeholderData: keepPreviousData,
    // keep the list's status pills current while anything on this page is processing
    refetchInterval: (q) => (q.state.data?.items.some(active) ? 5_000 : false),
  });
}

/** Poll while the job is processing: 2 s, backing off to 10 s; stop once it is finished. */
export function jobPollInterval(updates: number): number {
  return Math.min(2_000 * 1.25 ** updates, 10_000);
}

export function useJob(id: string) {
  return useQuery({
    queryKey: keys.job(id),
    queryFn: ({ signal }) => request<Job>(`/api/v1/jobs/${encodeURIComponent(id)}`, { signal }),
    refetchInterval: (q) => (active(q.state.data) ? jobPollInterval(q.state.dataUpdateCount) : false),
    refetchIntervalInBackground: false,
  });
}

export function useUsage(params: Record<string, string> = {}) {
  return useQuery({
    queryKey: keys.usage(params),
    queryFn: ({ signal }) => request<UsageReport>("/api/v1/usage", { query: params, signal }),
    staleTime: 30_000,
  });
}

export function useHealth() {
  return useQuery({
    queryKey: keys.health,
    queryFn: ({ signal }) => request<Health>("/api/health", { auth: false, signal }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
