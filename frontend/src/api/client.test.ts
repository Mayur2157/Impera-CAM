import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, parseError, request, setUnauthorizedHandler, url } from "./client";
import { setToken } from "./token";

function respond(status: number, body: unknown, headers: Record<string, string> = {}) {
  return vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json", ...headers },
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(null);
  setToken(null);
});

describe("parseError", () => {
  it("turns FastAPI validation errors into per-field messages", () => {
    const e = parseError(
      422,
      {
        detail: [
          { loc: ["body", "accept_terms"], msg: "Value error, accept the terms and privacy notice" },
          { loc: ["body", "password"], msg: "String should have at least 8 characters" },
        ],
      },
      null,
    );
    expect(e.fields).toEqual({
      accept_terms: "accept the terms and privacy notice",
      password: "String should have at least 8 characters",
    });
    expect(e.message).toBe("accept the terms and privacy notice");
  });

  it("says when to retry after a rate limit", () => {
    const e = parseError(429, { detail: "too many attempts — wait a minute and try again" }, "60");
    expect(e.message).toBe("Too many attempts — wait a minute and try again. Try again in 60 s.");
    expect(e.retryAfter).toBe(60);
  });
});

describe("request", () => {
  it("sends the session token and drops empty query values", async () => {
    const fetchMock = respond(200, { items: [], total: 0 });
    vi.stubGlobal("fetch", fetchMock);
    setToken("tok");
    await request("/api/v1/jobs", { query: { limit: 20, offset: 0, q: "" } });
    const [calledUrl, init] = fetchMock.mock.calls[0]!;
    expect(calledUrl).toBe("/api/v1/jobs?limit=20&offset=0");
    expect(init.headers).toEqual({ Authorization: "Bearer tok" });
  });

  it("ends the session on a 401, but not for sign-in", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);

    vi.stubGlobal("fetch", respond(401, { detail: "incorrect email or password" }));
    await expect(request("/api/auth/login", { auth: false })).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).not.toHaveBeenCalled();

    vi.stubGlobal("fetch", respond(401, { detail: "Invalid or expired token" }));
    await expect(request("/api/auth/me")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("reports an unreachable server in plain words", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(request("/api/v1/jobs")).rejects.toMatchObject({
      status: 0,
      message: "Can't reach Impera CAM — check your connection and try again.",
    });
  });

  it("builds URLs without a trailing ?", () => {
    expect(url("/api/v1/usage")).toBe("/api/v1/usage");
  });
});
