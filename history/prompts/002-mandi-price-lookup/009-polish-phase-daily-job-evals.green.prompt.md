---
id: 009
title: Polish phase daily job and evals
stage: green
date: 2026-09-27
surface: agent
model: claude-opus-5-5
feature: 002-mandi-price-lookup
branch: 002-mandi-price-lookup
user: hussainbuksh.noorani
command: continue
labels: ["polish", "cron", "purge", "eval", "security", "performance", "quickstart"]
links:
  spec: specs/002-mandi-price-lookup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/kisan/jobs/daily.py, src/kisan/jobs/purge.py, src/kisan/jobs/fetch_prices.py
  - src/kisan/app.py, src/kisan/config.py, src/kisan/db/migrations/env.py
  - data/sample_prices.yaml, vercel.json, pyproject.toml, requirements.txt
  - tests/contract/test_daily_job.py, tests/integration/test_purge.py
  - tests/eval/test_golden.py, tests/eval/test_conversations.py, tests/eval/conversations.yaml
  - specs/002-mandi-price-lookup/{research,tasks,quickstart}.md, contracts/webhooks.openapi.yaml
  - specs/002-mandi-price-lookup/checklists/{security,performance}.md
tests:
  - 276 passed; SC-001 100% (56/56), SC-006 100% (12/12); load test 150 msgs @5/s median 25 ms p95 35 ms; pip-audit clean
---

## Prompt

continue

## Response snapshot

T067 gate recorded (dictionary-only 100%, LLM fallback not built). Added /jobs/daily (CRON_SECRET, Vercel Cron 06:00 PKT) that refreshes enabled sources and purges 90-day-old turns (T074); verified live. SC-001/SC-006 now measured and enforced (T086). Security review with findings; removed unused anthropic dependency (T075). Local load test (T078). Quickstart run on a clean clone found alembic ignored .env — fixed, plus a no-Docker section (T080). 80/87 tasks done; remaining 7 need the owner.

## Outcome

- ✅ Impact: all developer-doable tasks for 002 complete; live demo stays fresh daily
- 🧪 Tests: 276 passing
- 📁 Files: see list
- 🔁 Next prompts: owner tasks (AMIS permission letter, SMS vendor, native review, pilot); fix security findings F1–F4 before pilot
- 🧠 Reflection: running the quickstart on a clean clone found a real onboarding bug the test suite could not

## Evaluation notes (flywheel)

- Failure modes observed: persistent local pgserver would not restart after an unclean shutdown; Vercel ls commit filter didn't match
- Graders run and results (PASS/FAIL): pytest PASS, ruff PASS, mypy PASS, pip-audit PASS, live /health and /jobs/daily PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
