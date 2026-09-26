# Research: To-Do App

**Feature**: 001-todo-app | **Date**: 2026-09-26

All Technical Context unknowns are resolved below. Each decision favors the fewest moving parts
that still satisfy the constitution (Principle V).

## R1. Language and runtime

- **Decision**: TypeScript 5.x on Node.js 24 for both frontend and backend.
- **Rationale**: Node 24 is installed; one language across the stack lets request/response types
  stay aligned with the contract; one package manager (npm).
- **Alternatives considered**: Python/FastAPI backend (two languages, two toolchains);
  Next.js single project (would need a Complexity Tracking justification against the
  frontend/backend split in the constitution).

## R2. Project layout

- **Decision**: npm workspaces monorepo with `backend/` and `frontend/`, each with its own `tests/`.
- **Rationale**: Matches the constitution's Web Application Constraints; one `npm install` and
  root scripts to run everything.
- **Alternatives considered**: Two unrelated repos (harder to keep contract and E2E in sync).

## R3. Storage

- **Decision**: SQLite via Node's built-in `node:sqlite` (`DatabaseSync`), plain parameterized SQL,
  numbered `.sql` migration files applied at startup and tracked in a `schema_migrations` table.
  Foreign keys ON with `ON DELETE CASCADE` for list → tasks. WAL mode.
- **Rationale**: Zero install (no Docker/PostgreSQL on the machine), no native compilation
  (verified working on this machine), parameterized statements satisfy OWASP injection rules.
  Data volume (thousands of tasks per user) is well within SQLite's range.
- **Alternatives considered**: `better-sqlite3` (native build step on Windows); PostgreSQL
  (requires a server); an ORM such as Prisma/Drizzle (extra layer not needed for 4 tables).

## R4. HTTP framework and validation

- **Decision**: Express 5 with `zod` schemas validating every request body, query, and path
  parameter on the server; errors returned in one shape `{ error: { code, message, fields? } }`.
- **Rationale**: Express 5 forwards async errors natively; zod gives per-field messages
  (FR-019) and inferred TypeScript types.
- **Alternatives considered**: Fastify (fine, but no advantage at this scale); manual validation
  (error-prone).

## R5. Authentication and sessions

- **Decision**: Email + password. Passwords hashed with Node `crypto.scrypt` (N=2^15, r=8, p=1,
  16-byte salt, 64-byte key), compared with `timingSafeEqual`. Server-side sessions: random 32-byte
  token in an `HttpOnly; SameSite=Lax; Secure (in production); Path=/` cookie, stored in a
  `sessions` table as a SHA-256 hash with a 7-day sliding expiry. Sign-out deletes the session row.
- **Rationale**: No native dependencies; server-side sessions can be revoked; hashing the token
  means a leaked DB does not leak live sessions.
- **Alternatives considered**: JWT (hard to revoke, no benefit for a single backend); argon2
  (native module); third-party auth provider (out of scope per spec Assumptions).

## R6. CSRF, rate limiting, security headers

- **Decision**:
  - CSRF: `SameSite=Lax` cookie plus a server check that state-changing requests
    (POST/PATCH/DELETE) have `Content-Type: application/json` and an `Origin` matching the
    configured app origin.
  - Sign-in throttling (FR-006): per-email failed-attempt counter in a `login_attempts` table;
    after 5 failures within 15 minutes, sign-in for that email returns 429 until the window ends.
    Plus a coarse per-IP limit on auth routes via `express-rate-limit`.
  - Security headers via `helmet`.
  - Sign-up for an existing email returns a generic 409 "Unable to create account with these
    details".
- **Rationale**: Covers OWASP A01/A03/A05/A07 for this app with small, well-known libraries.
- **Alternatives considered**: Synchronizer CSRF tokens (unnecessary with same-origin JSON API
  plus SameSite and Origin checks).

## R7. Authorization

- **Decision**: Every list/task query is scoped by `user_id` in SQL
  (`WHERE id = ? AND user_id = ?`). Access to a resource the user does not own returns **404**
  (not 403) so existence is not revealed (spec US2 scenario 5).
- **Rationale**: Ownership enforced at the data-access layer cannot be bypassed by a missing
  route check.

## R8. Pagination, sorting, filtering

- **Decision**: Server-side. `GET /api/lists/{id}/tasks?status=all|open|done&sort=created|due|priority&page=1&pageSize=50`
  (pageSize max 100). Response includes `total`. Lists endpoint paginated the same way.
  Due-date sort: `due_date IS NULL, due_date ASC, id ASC`. Priority stored as integer
  (1=Low, 2=Medium, 3=High) so sort is `priority DESC, id ASC`. Indexes on
  `tasks(list_id, created_at)`, `tasks(list_id, due_date)`, `tasks(list_id, priority)`.
- **Rationale**: Meets FR-015–FR-018 and SC-004 (1,000 tasks) without loading everything;
  avoids N+1 by fetching one page with one query.

## R9. Overdue calculation

- **Decision**: Computed in the frontend: a task is overdue when `done = false` and
  `dueDate < today` in the browser's local date. Dates are stored and transferred as
  `YYYY-MM-DD` strings.
- **Rationale**: The spec defines "today" as the user's local date, which only the client knows.
  Pure function, fully unit-testable.

## R10. Frontend

- **Decision**: React 19 + Vite + React Router; data fetching through a small typed `api` client
  (`fetch`, `credentials: 'include'`); plain CSS modules. Vite dev server proxies `/api` to the
  backend so the cookie is same-origin. In production the backend serves the built frontend.
- **Rationale**: Minimal dependency set; same-origin avoids CORS entirely.
- **Alternatives considered**: TanStack Query (useful later; not needed for simple
  load-after-mutation flows); a component library (accessibility of custom markup is covered by
  semantic HTML + axe checks).

## R11. Observability

- **Decision**: `pino` + `pino-http` JSON logs. Each request gets an `X-Request-Id` (accepted from
  the client if it is a UUID, otherwise generated), returned in the response header and attached to
  every log line. The frontend api client sends a UUID `X-Request-Id` per request. Unhandled errors
  are logged at `error` level with the request ID and an `errorId`; clients receive only
  `{ error: { code: "INTERNAL", message, errorId } }`. `GET /api/health` returns DB status.
  Passwords, session tokens, and cookies are redacted via pino `redact`.
- **Rationale**: Satisfies Principle VI with no external service. A hosted error tracker (e.g.
  Sentry) can be added when the app is deployed; the single error handler is the only change point.
- **Alternatives considered**: Hosted error tracking now (no deployment target yet — YAGNI).

## R12. Testing and quality gates

- **Decision**:
  - Backend: Vitest + Supertest; contract tests validate responses against `contracts/openapi.yaml`
    (via `openapi-response-validator` style check using `ajv`); integration tests use a fresh
    in-memory SQLite per test file.
  - Frontend: Vitest + React Testing Library + `jsdom`; the api client is mocked at the `fetch`
    boundary with MSW.
  - E2E: Playwright (Chromium) against the real backend with a temporary database file;
    `@axe-core/playwright` asserts zero WCAG 2.1 A/AA violations on each P1 page.
  - Coverage: `@vitest/coverage-v8`, thresholds 80% lines per workspace.
  - Performance: a backend test seeds 1,000 tasks and asserts task-page responses under 300 ms;
    Lighthouse CI budget (LCP < 2.5 s, CLS < 0.1) on the built app.
  - CI: GitHub Actions — lint, typecheck, unit/integration, E2E, coverage, `npm audit --audit-level=high`.
- **Rationale**: Covers every layer required by Principles II–III and VII with deterministic
  tests (no real external services; time controlled with fake timers).
