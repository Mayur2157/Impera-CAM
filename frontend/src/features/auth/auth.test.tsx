import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter } from "react-router";
import { RouterProvider } from "react-router/dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/auth/AuthProvider";
import { routes } from "@/routes";

const ME = {
  id: "u1",
  email: "analyst@lender.example",
  role: "owner",
  is_superuser: false,
  tenant_id: "t1",
  org_name: "Demo Lending",
  org_status: "active",
  plan: "free",
};

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/** A fake backend: answers by path, records what was sent. */
function backend(handlers: Record<string, (init: RequestInit) => Response>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const path = String(input).split("?")[0]!;
    const handler = handlers[path];
    return handler ? handler(init) : json(404, { detail: "not found" });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return router;
}

afterEach(() => vi.unstubAllGlobals());

describe("sign in", () => {
  it("sends a signed-out visitor to sign-in, then back where they were going", async () => {
    const user = userEvent.setup();
    backend({
      "/api/auth/login": () => json(200, { access_token: "tok", token_type: "bearer" }),
      "/api/auth/me": () => json(200, ME),
      "/api/v1/jobs": () => json(200, { items: [], total: 0 }),
    });
    const router = renderAt("/app/statements");

    expect(router.state.location.pathname).toBe("/login");
    await user.type(await screen.findByLabelText("Email"), "analyst@lender.example");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "No statements yet" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/app/statements");
    expect(sessionStorage.getItem("icam.token")).toBe("tok");
  });

  it("labels missing fields and announces a wrong password", async () => {
    const user = userEvent.setup();
    backend({ "/api/auth/login": () => json(401, { detail: "incorrect email or password" }) });
    renderAt("/login");

    await user.click(await screen.findByRole("button", { name: "Sign in" }));
    expect(screen.getByLabelText("Email")).toHaveAccessibleDescription("Enter your email address");
    expect(screen.getByLabelText("Email")).toHaveFocus();

    await user.type(screen.getByLabelText("Email"), "analyst@lender.example");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("don't match an account");
    expect(sessionStorage.getItem("icam.token")).toBeNull();
  });
});

describe("sign up", () => {
  it("requires consent, and puts a taken email on the email field", async () => {
    const user = userEvent.setup();
    const fetchMock = backend({
      "/api/auth/register": () => json(409, { detail: "email already registered" }),
    });
    renderAt("/signup");

    await user.type(await screen.findByLabelText("Organisation name"), "Demo Lending");
    await user.type(screen.getByLabelText("Work email"), "analyst@lender.example");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    const consent = screen.getByRole("checkbox");
    expect(consent).not.toBeChecked(); // never pre-ticked
    expect(consent).toHaveAccessibleDescription("Tick the box to agree before creating the account");
    expect(fetchMock).not.toHaveBeenCalled();

    await user.click(consent);
    await user.click(screen.getByRole("button", { name: "Create account" }));
    const sent = JSON.parse(String(fetchMock.mock.calls[0]![1]!.body));
    expect(sent).toEqual({
      org_name: "Demo Lending",
      email: "analyst@lender.example",
      password: "password123",
      accept_terms: true,
    });
    expect(
      await screen.findByText("An account already uses this email. Sign in instead."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Work email")).toHaveFocus();
  });
});
