# Impera CAM portal — Prompt 1: Foundation

Build the foundation from your prompt pack, step by step. Prompts 2–7 follow once you've checked this one in mock mode (`demo@impera.test` / `demo1234`).

## Adaptations to this project
- Routing uses TanStack Router (the project's fixed router) instead of React Router. Same URLs, same behaviour.
- No Lovable Cloud: all data goes through one API client, answered by the in-memory mock server while `VITE_USE_MOCKS=true` (the default).
- Your Knowledge and API CONTRACT get saved into project memory, so later prompts stick to them.

## What gets built
1. **Design system "Ledger, modernised"**: the light and dark palette tokens (follows the system setting, with a toggle), plus Inter, Source Serif 4 and JetBrains Mono fonts. Shared components: Money (₹ in en-IN grouping), MaskedAccount, StatusPill, BalanceCheckBadge, RiskGradeBadge, ScoreGauge, EmptyState, ErrorState, PageHeader, DataTable (sortable, paginated, turns into cards below 640px), CopyButton, ConfirmDialog, and toasts read out by screen readers.
2. **API layer**: a typed fetch client (base URL, Bearer token in memory plus sessionStorage, JSON and file responses, errors turned into `{status, message, retryAfter}`). Every contract shape gets a type, and every endpoint gets a query hook. A 401 sends the user to `/login?next=`. A 403 shows an inline "no permission" message.
3. **Mock server**: implements every contract endpoint. Seed data: Demo Lending Pvt Ltd (owner, member, superuser `staff@impera.test`), 3 finished jobs, 1 running job that finishes in about 10 seconds, 2 API keys, 30 days of usage. Adding `?mockError=401|403|429|503` forces an error.
4. **Sign-in pages**: `/login`, `/signup` (password strength meter, unticked consent box linking to privacy and terms) and `/invite/$token`. After sign-in the user goes to `/app`, or back to the page in `?next=`.
5. **App shell `/app/*`**: sidebar with Dashboard, Statements, API keys, Usage, Team, Settings, Docs, and Admin for superusers only. Top bar with org name, plan badge and user menu (change password, theme, sign out). The sidebar collapses on mobile. Suspended orgs see a read-only banner. Pages are guarded by role. Pages from later prompts show a simple "coming next" placeholder for now.
6. **Public pages**: landing page at `/` (hero, 3 steps, balance-check explainer, API snippet, security/DPDP section, call to action), `/pricing`, `/privacy` and `/terms` (marked DRAFT), and a 404 page.

## Technical details
- `src/lib/api/{client,types,hooks}.ts`, `src/lib/api/mocks/*` (with a simulated delay and the job progress ticking forward).
- Auth context in `src/lib/auth.tsx`. `/app` is a layout route whose guard is client-side, since the token lives in sessionStorage.
- Routes: `index, pricing, privacy, terms, login, signup, invite.$token, app (layout), app.index, app.statements, app.api-keys, app.usage, app.team, app.settings, app.docs, app.admin`. Each route gets its own head() with no personal data in titles.
- Tokens go in `src/styles.css` (oklch) and fonts via a link in `__root`. Toaster is mounted in root.
- Formatting helpers: `formatINR` and `formatDate` (dd MMM yyyy), `maskAccount` and `maskPAN`.
- Add zod, react-hook-form and recharts if they're missing.
- Record the architecture rules (single API client, mock mode, no Cloud) in AGENTS.md.
