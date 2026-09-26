# Data Model: To-Do App

**Feature**: 001-todo-app | **Storage**: SQLite (`node:sqlite`) | **Date**: 2026-09-26

All timestamps are ISO-8601 UTC strings. IDs are integer primary keys (never exposed as proof of
access — every query is also scoped by `user_id`).

## users

| Field | Type | Rules |
|---|---|---|
| id | INTEGER PK | auto |
| email | TEXT | required, trimmed, lower-cased, valid email, ≤ 254 chars, **UNIQUE** |
| password_hash | TEXT | scrypt `salt:hash` (hex); never returned by the API |
| created_at | TEXT | set on insert |

## sessions

| Field | Type | Rules |
|---|---|---|
| token_hash | TEXT PK | SHA-256 of the cookie token |
| user_id | INTEGER FK → users.id | ON DELETE CASCADE |
| expires_at | TEXT | now + 7 days; extended on use (sliding) |
| created_at | TEXT | set on insert |

Expired sessions are treated as absent and deleted when encountered.

## login_attempts

| Field | Type | Rules |
|---|---|---|
| email | TEXT PK | normalized email (row may exist for unknown emails too) |
| failed_count | INTEGER | incremented on failure |
| window_started_at | TEXT | start of the current 15-minute window |

Reset on successful sign-in or when the window has elapsed. 5 failures in the window → 429.

## lists

| Field | Type | Rules |
|---|---|---|
| id | INTEGER PK | auto |
| user_id | INTEGER FK → users.id | ON DELETE CASCADE; required |
| name | TEXT | trimmed, 1–100 chars; duplicates allowed |
| created_at | TEXT | set on insert |
| updated_at | TEXT | set on insert/update |

Index: `(user_id, created_at)`.

## tasks

| Field | Type | Rules |
|---|---|---|
| id | INTEGER PK | auto |
| list_id | INTEGER FK → lists.id | ON DELETE CASCADE; required |
| user_id | INTEGER FK → users.id | ON DELETE CASCADE; denormalized owner for single-query authorization |
| title | TEXT | trimmed, 1–200 chars |
| due_date | TEXT NULL | `YYYY-MM-DD`, must be a real calendar date; past dates allowed |
| priority | INTEGER | 1 = Low, 2 = Medium (default), 3 = High |
| done | INTEGER | 0/1, default 0 |
| created_at | TEXT | set on insert |
| updated_at | TEXT | set on insert/update |

Indexes: `(list_id, created_at)`, `(list_id, due_date)`, `(list_id, priority)`.
Invariant: `tasks.user_id` always equals the owning list's `user_id` (set by the server from the
list lookup, never from client input).

## Relationships

```text
User 1 ──< Session
User 1 ──< List 1 ──< Task
```

## State transitions

- **Task.done**: `false ⇄ true` via PATCH; no other states. "Overdue" is derived, not stored:
  `done = false AND due_date < user's local today`.
- **Session**: created on sign-up/sign-in → extended on each authenticated request → deleted on
  sign-out or when expired.

## API representation

Priority is exposed as `"low" | "medium" | "high"`; `done` as boolean; `dueDate` as
`YYYY-MM-DD | null`. Field names are camelCase in JSON. See `contracts/openapi.yaml`.
