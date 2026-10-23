<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture rules
- No Lovable Cloud/Supabase: all data comes from the external FastAPI REST API; never invent endpoints outside the API contract (see mem://reference/api-contract).
- Every request goes through `src/lib/api/client.ts`; contract types live in `src/lib/api/types.ts`; query hooks in `src/lib/api/hooks.ts` — one place to change transport.
- Mock mode (`VITE_USE_MOCKS` !== "false", default on) routes requests to `src/lib/api/mocks/` which must implement every contract endpoint — lets the UI run before the backend exists.
- Auth token lives in memory + sessionStorage only (`src/lib/api/token.ts`); `/app` is `ssr: false` and guarded client-side because the token is not visible to SSR.
- Shared ledger UI (badges, states, DataTable, dialogs) lives in `src/components/ledger/` — reuse before creating new primitives.
