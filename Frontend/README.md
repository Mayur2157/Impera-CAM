# Welcome to your Lovable project

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Open your project in the [Lovable editor](https://lovable.dev) and keep building.

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: connect the project to GitHub and every change made in Lovable is committed straight to your repository.
- **Full ownership**: this code is yours. Push to your repository and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```

## Built with

- TanStack Start
- TypeScript
- React
- Tailwind CSS

## Impera CAM portal — configuration

All data comes from the Impera CAM REST API. Every request goes through
`src/lib/api/client.ts`; no other file calls `fetch`.

### Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `VITE_USE_MOCKS` | `true` | `true` uses the built-in demo server in `src/lib/api/mocks/`. Set to `false` to call the real backend. |
| `VITE_API_BASE_URL` | empty | Backend base URL, e.g. `https://api.example.com` (no trailing slash). Also shown in the API docs and code samples. |

See `.env.example`.

### Run with mocks (default)

```sh
npm i
npm run dev
```

Demo accounts (password `demo1234`): `demo@impera.test` (owner), `member@impera.test` (member),
`staff@impera.test` (Impera staff — opens the staff console at `/admin`).

Testing helpers, added to any page URL in mock mode:
- `?mockError=500|503|401|403|429` — force that error on every request (except sign-in).
- `?mockOcr=none` — pretend no OCR worker is online (dashboard notice, staff alert).

### Point at a real backend

```sh
VITE_USE_MOCKS=false VITE_API_BASE_URL=https://api.example.com npm run dev
```

No code changes are needed. The backend must allow CORS from the portal's origin and
implement the API contract (auth, jobs, API keys, usage, org, admin, health).

### Security notes
- The session token is kept in memory and `sessionStorage` only (never `localStorage`), and
  is cleared on sign-out or any 401.
- API key secrets are shown once after creation and never stored by the portal.
- No personal data in URLs, page titles or logs.
