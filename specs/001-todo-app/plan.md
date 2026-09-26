# Implementation Plan: To-Do App

**Branch**: `001-todo-app` | **Date**: 2026-09-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-todo-app/spec.md`

## Summary

A web to-do app where users sign up and sign in with email and password, manage private task
lists, and add tasks with an optional due date and a priority, mark them done, and sort/filter
them with overdue highlighting. Built as a TypeScript monorepo: a React (Vite) frontend and an
Express 5 JSON API backed by SQLite through Node's built-in `node:sqlite`, with server-side
sessions, per-user data scoping in every query, and tests at unit, contract/integration, and
E2E (with axe accessibility checks) layers. See [research.md](./research.md) for decisions.

## Technical Context

**Language/Version**: TypeScript 5.x on Node.js 24 (frontend and backend)
**Primary Dependencies**: Backend — Express 5, zod, helmet, express-rate-limit, pino, pino-http,
cookie-parser. Frontend — React 19, React Router, Vite.
**Storage**: SQLite file via built-in `node:sqlite`; SQL migrations applied at startup
**Testing**: Vitest (+ Supertest backend, React Testing Library + MSW frontend),
`@vitest/coverage-v8`, Playwright + `@axe-core/playwright`, ajv for contract validation
**Target Platform**: Modern evergreen browsers (desktop + mobile widths); Node 24 server
(Windows/Linux)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: API p95 < 300 ms; LCP < 2.5 s; INP < 200 ms; CLS < 0.1; a 1,000-task list
page loads < 2.5 s (SC-004); UI updates < 1 s for 95% of actions (SC-003)
**Constraints**: Pagination max 100 items/page; no committed secrets (config from `.env`);
same-origin cookie auth; WCAG 2.1 AA
**Scale/Scope**: Single-instance app; up to ~1,000 users and ~1,000 tasks per list;
~6 screens (sign up, sign in, lists, list detail, task edit, not found)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Test-First**: `/sp.tasks` will place failing contract/integration/unit tests before
  implementation for every user story; bug fixes start with a reproducing test.
- [x] **II. Tests at Every Layer**: Unit (services, validators, `isOverdue`, React components),
  contract (every endpoint validated against `contracts/openapi.yaml`), integration (API + real
  SQLite in-memory), E2E (Playwright for US1–US3 P1 journeys). External boundaries mocked
  (MSW on frontend); time controlled via fake timers.
- [x] **III. Tests Define Done**: Each acceptance scenario in spec.md maps to at least one test
  (tracked in tasks.md); 80% line-coverage threshold per workspace enforced in CI.
- [x] **IV. Security by Default**: Public endpoints: `GET /health`, `POST /auth/signup`,
  `POST /auth/signin` only; all others require a session. Ownership enforced in SQL
  (`user_id = ?`), cross-user access → 404 with tests for allowed and denied. scrypt password
  hashing, hashed session tokens, HttpOnly/SameSite cookies, Origin + JSON content-type check
  (CSRF), helmet headers, sign-in throttling (5/15 min per email) plus per-IP limit, parameterized
  SQL only, React output escaping, `npm audit --audit-level=high` in CI.
- [x] **V. Simplicity**: No ORM, no state-management library, no data-fetching library, no
  external services; built-in SQLite and crypto. Every dependency above has a single stated
  purpose. No Complexity Tracking entries required.
- [x] **VI. Observability**: pino JSON logs with `X-Request-Id` correlation (frontend → API → DB
  log lines), redaction of password/cookie/token fields, central error handler logging an
  `errorId` without leaking internals, `GET /api/health` checking the DB.
- [x] **VII. Accessibility & Performance**: Semantic HTML forms with labels, keyboard operable
  controls, visible focus, live-region announcements for errors; axe checks in E2E for every P1
  page; budgets as listed in Performance Goals, verified by a 1,000-task backend perf test and
  Lighthouse CI; server-side pagination on lists and tasks; single-query page fetches (no N+1).
- [x] **Web Constraints**: Separate `frontend/` and `backend/` projects each with `tests/`;
  OpenAPI contract written (Phase 1) before endpoints; zod validation on the server for body,
  query, and path; config via environment variables with `.env.example` committed and `.env`
  git-ignored.

**Result**: PASS (pre-design and post-design). No violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-todo-app/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 entities, rules, indexes
├── quickstart.md        # Phase 1 run/test/validate guide
├── contracts/
│   └── openapi.yaml     # Phase 1 API contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/sp.tasks — not created here)
```

### Source Code (repository root)

```text
package.json                     # npm workspaces: backend, frontend; root scripts
.github/workflows/ci.yml         # lint, typecheck, tests, coverage, e2e, npm audit
.gitignore                       # node_modules, dist, .env, *.db

backend/
├── package.json
├── tsconfig.json
├── vitest.config.ts
├── .env.example
├── migrations/
│   └── 001_init.sql             # users, sessions, login_attempts, lists, tasks + indexes
├── src/
│   ├── server.ts                # entry: load config, open DB, migrate, listen
│   ├── app.ts                   # createApp(deps): middleware + routes (testable)
│   ├── config.ts                # env parsing (zod)
│   ├── db/
│   │   ├── connection.ts        # DatabaseSync open, pragmas (FK, WAL)
│   │   └── migrate.ts           # apply numbered migrations
│   ├── middleware/
│   │   ├── requestId.ts         # X-Request-Id
│   │   ├── originCheck.ts       # CSRF: Origin + JSON content-type
│   │   ├── requireAuth.ts       # session → req.user
│   │   ├── validate.ts          # zod body/query/params
│   │   └── errorHandler.ts      # error shape, errorId, logging
│   ├── auth/
│   │   ├── password.ts          # scrypt hash/verify
│   │   ├── sessions.ts          # create/lookup/extend/delete
│   │   ├── loginThrottle.ts     # 5 failures / 15 min per email
│   │   └── routes.ts            # /auth/*
│   ├── lists/
│   │   ├── schemas.ts
│   │   ├── repository.ts        # SQL scoped by user_id
│   │   └── routes.ts            # /lists, /lists/:id
│   ├── tasks/
│   │   ├── schemas.ts
│   │   ├── repository.ts        # SQL scoped by user_id; sort/filter/paginate
│   │   └── routes.ts            # /lists/:id/tasks, /tasks/:id
│   ├── health/routes.ts
│   └── lib/
│       ├── errors.ts            # AppError types → codes/statuses
│       ├── logger.ts            # pino with redaction
│       └── pagination.ts
└── tests/
    ├── helpers/                 # test app factory (in-memory DB), auth helpers, contract validator
    ├── contract/                # every endpoint vs openapi.yaml
    ├── integration/             # auth, lists, tasks, authorization, throttling, perf (1,000 tasks)
    └── unit/                    # password, sessions, throttle, schemas, pagination, errors

frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts               # /api proxy → backend
├── vitest.config.ts
├── playwright.config.ts
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx                  # routes + auth guard
│   ├── api/
│   │   ├── client.ts            # typed fetch, X-Request-Id, error mapping
│   │   └── types.ts             # types mirroring openapi.yaml
│   ├── auth/
│   │   ├── AuthContext.tsx
│   │   ├── SignInPage.tsx
│   │   └── SignUpPage.tsx
│   ├── lists/
│   │   ├── ListsPage.tsx
│   │   └── ListForm.tsx
│   ├── tasks/
│   │   ├── ListDetailPage.tsx   # tasks + sort/filter/pagination
│   │   ├── TaskForm.tsx
│   │   ├── TaskItem.tsx
│   │   └── isOverdue.ts
│   ├── components/              # FormField, ConfirmDialog, Pagination, ErrorMessage
│   └── styles/
└── tests/
    ├── unit/                    # components, isOverdue, api client (MSW)
    └── e2e/                     # Playwright: US1–US4 journeys + axe checks
```

**Structure Decision**: Web application layout (constitution default) with npm workspaces.
Backend modules are grouped by domain (`auth`, `lists`, `tasks`) with a thin repository per
domain holding all SQL; `createApp(deps)` takes the DB handle so tests run against an in-memory
database. The frontend mirrors the same domains. The backend serves `frontend/dist` in
production so the app is single-origin.

## Architectural Decisions (candidates for ADRs)

1. **Server-side sessions in SQLite over JWT** — revocable, simple, same-origin.
2. **SQLite via `node:sqlite` with raw SQL over an ORM/PostgreSQL** — zero setup, no native build.
3. **Cross-user access returns 404** — hides existence of other users' data.

## Complexity Tracking

No constitution violations; nothing to justify.
