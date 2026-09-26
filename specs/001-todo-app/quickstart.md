# Quickstart: To-Do App

**Prerequisites**: Node.js 24+, npm 11+. No database server needed (SQLite file).

## Run locally

```bash
npm install                 # installs root, backend, and frontend workspaces
cp backend/.env.example backend/.env
npm run dev                 # backend on :3000, frontend on :5173 (proxies /api → :3000)
```

Open http://localhost:5173.

### Backend environment (`backend/.env`)

| Variable | Example | Purpose |
|---|---|---|
| `PORT` | `3000` | API port |
| `DATABASE_PATH` | `./data/todo.db` | SQLite file (created automatically) |
| `APP_ORIGIN` | `http://localhost:5173` | Allowed `Origin` for state-changing requests |
| `NODE_ENV` | `development` | `production` enables `Secure` cookies |
| `LOG_LEVEL` | `info` | pino log level |

## Test

```bash
npm test                    # backend + frontend unit/integration/contract tests
npm run test:coverage       # same, with 80% line-coverage gate
npm run test:e2e            # Playwright E2E + axe accessibility checks (starts servers)
npm run lint && npm run typecheck
npm audit --audit-level=high
```

## Validate the feature manually (maps to spec acceptance scenarios)

1. **US1**: Sign up with `a@example.com` / `password123` → lands on "Your lists". Sign out →
   visiting `/lists` redirects to sign-in. Sign in with a wrong password → "Invalid email or
   password". Sign in correctly → back to lists.
2. **US2**: Create list "Work" → appears. Rename to "Office" → name updates. Try an empty name →
   field error. Sign up as `b@example.com` in a private window, open `/lists/<A's list id>` →
   "Not found".
3. **US3**: In "Office", add "Write report" (title only) → Medium, no due date, not done. Add
   "Pay rent", due tomorrow, High. Mark "Write report" done, then undone. Edit and delete a task.
4. **US4**: Add a task due yesterday → marked overdue; mark it done → no longer overdue. Sort by
   due date and by priority; filter Open/Done.
5. **Health**: `curl http://localhost:3000/api/health` → `{"status":"ok","db":"ok"}` with an
   `X-Request-Id` header.

## Production build

```bash
npm run build               # builds frontend into frontend/dist and compiles backend
NODE_ENV=production npm start   # backend serves API at /api and the built frontend
```
