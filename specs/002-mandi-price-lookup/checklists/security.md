# Security & Privacy Review: Mandi Price Lookup (T075)

**Date**: 2026-09-27 | **Scope**: `src/kisan/`, `app.py`, deployment on Vercel + Neon
**Constitution**: Principle IV (Security & Farmer Privacy)

## Checks

- [x] **Dependency scan** — `pip-audit -r requirements.txt`: no known vulnerabilities.
- [x] **No phone numbers at rest** — tables key conversations by `contact_hash` (HMAC with a
  secret pepper); no column holds a number (`src/kisan/db/models.py`).
- [x] **Redaction** — CNIC and phone numbers replaced with `[CNIC]` / `[PHONE]` before message
  text is stored (FR-018); verified locally in the stored turn and by
  `tests/unit/test_redact.py`, `tests/unit/test_logging_privacy.py`.
- [x] **Logs** — no log call passes message text, numbers, or raw contacts; captured-log test
  asserts numbers, CNIC and message text never appear. Unhandled errors log type + location
  only (`observability.capture_exception`).
- [x] **Webhook authentication** — WhatsApp `X-Hub-Signature-256` HMAC verified before parsing;
  SMS path secret; `/jobs/daily` bearer secret; all compared with `hmac.compare_digest`.
- [x] **Denial tests** — missing/invalid signature, wrong verify token, wrong SMS secret,
  malformed payloads, missing/wrong cron secret, cron route off when unconfigured
  (`tests/contract/`).
- [x] **Repeated deliveries** answered once (FR-019, `tests/integration/test_dedupe.py`).
- [x] **No personal data requested** — catalogue scan for CNIC/account/PIN/OTP wording
  (`tests/unit/test_catalogue_privacy.py`).
- [x] **Prompt injection** — no LLM in the request path (T067 gate); injection phrasings in the
  eval set cannot change prices, which come only from the database.
- [x] **Secrets** — none in git (`.env*`, `.pgdata/` ignored); Vercel values stored as
  sensitive env vars; data retention: turns purged after 90 days by `/jobs/daily`.

## Findings (open)

| # | Risk | Severity | Action |
|---|------|----------|--------|
| F1 | The SMS webhook secret is part of the URL path, so it appears in hosting request logs. | Medium | When the SMS vendor is chosen (T076), prefer a header secret or signature; rotate `SMS_WEBHOOK_SECRET` if logs are shared. |
| F2 | No rate limiting on webhooks; anyone holding a secret could flood the bot (cost, DB load). | Low | Add per-contact rate limiting before the pilot, or rely on the provider's own limits. |
| F3 | The demo deployment has the sample ("Test data") price source enabled. Replies are labelled "Test data", but farmers must never see it. | High before pilot | Disable the fixture source (`UPDATE price_sources SET enabled=false WHERE id='fixture'`) before any real farmer uses the number. |
| F4 | `/docs` and `/openapi.json` are public on the demo. | Low | Turn off docs in production when WhatsApp goes live. |
| F5 | `anthropic` was an unused dependency (LLM fallback not built). | Low | **Fixed 2026-09-27**: removed from pyproject.toml and requirements.txt; re-add with T071 if the gate fails. |
| F6 | The live demo secrets have a plain-text local copy in git-ignored `.env.vercel-demo`. | Low | Keep it off shared drives; rotate after demos. |
