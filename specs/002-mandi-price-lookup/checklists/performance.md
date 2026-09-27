# Performance Check: Mandi Price Lookup (T078)

**Date**: 2026-09-27 | **Targets** (FR-013, constitution VII): median reply < 5 s, p95 < 10 s

## Local load test

- Setup: local server (`uvicorn`, 1 worker) with `INLINE_REPLIES=true`, so each HTTP response
  time is the full time-to-reply (understanding + database lookup + reply rendering).
  Fresh PostgreSQL 16 (pgserver) with reference data and sample prices; Windows dev laptop.
- Load: 150 SMS webhook messages at 5 messages/s from 40 different numbers, mixing price
  questions (both scripts), paddy group words, follow-up questions, lists, unsupported crops,
  and greetings.
- Result: **0 errors; median 25 ms, p95 35 ms, max 46 ms.**

## Live (Vercel + Neon, 2026-09-26)

- Single SMS webhook requests with inline replies: 0.65–1.2 s end to end from Pakistan-time
  test client (includes network and cold start).

## Not covered

- WhatsApp / SMS provider delivery time (outside the system; SC-004 excludes carrier delays).
- Sustained load on Vercel (function concurrency, Neon connection limits) — re-test before
  the pilot with the real WhatsApp number.
