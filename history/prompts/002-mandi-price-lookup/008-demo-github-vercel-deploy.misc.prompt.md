---
id: 008
title: Demo, GitHub push and Vercel deploy
stage: misc
date: 2026-09-26
surface: agent
model: claude-opus-5-5
feature: 002-mandi-price-lookup
branch: 002-mandi-price-lookup
user: hussainbuksh.noorani
command: general
labels: ["deploy", "vercel", "neon", "github", "demo"]
links:
  spec: specs/002-mandi-price-lookup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - app.py
  - vercel.json
  - .vercelignore
  - requirements.txt
  - src/kisan/config.py
  - src/kisan/app.py
  - src/kisan/observability.py
  - tests/contract/test_inline_replies.py
  - tests/unit/test_config.py
  - ci/github-actions.yml
  - Dockerfile, CLAUDE.md, specs/002-mandi-price-lookup/quickstart.md
tests:
  - 268 passed; live checks: /health ok (Neon), SMS webhook replies in Roman Urdu and Urdu, wrong secret 401
---

## Prompt

now show me the app and deploye it to github and vercel
(then) do it all by yourself

## Response snapshot

Ran the app locally on pgserver with sample prices and showed a 9-message conversation over the SMS webhook. Fixed a Windows crash when logging Urdu. Added inline replies for serverless hosting and postgres:// URL support (tests first). Created private GitHub repo via the saved git credential and pushed; CI workflow parked because the token lacks workflow scope. Created Vercel project, provisioned Neon, migrated/seeded/loaded sample prices, deployed to https://kisan-assistant.vercel.app; fixed 404s by switching to a root app.py FastAPI entry point; verified live replies; connected the repo to Vercel.

## Outcome

- ✅ Impact: app live on Vercel with sample prices; code on GitHub
- 🧪 Tests: 268 passing; live smoke tests passed
- 📁 Files: see list
- 🔁 Next prompts: Vercel Cron for price refresh; enable CI (workflow scope); WhatsApp account; AMIS permission
- 🧠 Reflection: serverless needs replies inside the request; tests must check response timing, not just outcomes

## Evaluation notes (flywheel)

- Failure modes observed: winget unavailable; GitHub token without workflow scope; Vercel rewrite gave fixed path; Windows curl mangled Urdu JSON
- Graders run and results (PASS/FAIL): pytest PASS; live /health PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): add a Vercel Cron endpoint for the fetch job
