---
id: 010
title: Ufone, WhatsApp prep, rate limit, website
stage: misc
date: 2026-09-28
surface: agent
model: claude-opus-5-5
feature: 002-mandi-price-lookup
branch: 002-mandi-price-lookup
user: hussainbuksh.noorani
command: general
labels: ["sms-vendor", "whatsapp", "rate-limit", "website", "privacy-policy", "meta-verification"]
links:
  spec: specs/002-mandi-price-lookup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-mandi-price-lookup/research.md (T008 Ufone)
  - scripts/whatsapp_setup.py
  - src/kisan/conversation/handler.py (rate limit), tests/integration/test_rate_limit.py
  - src/kisan/site.py, data/business.yaml, tests/contract/test_site.py
  - specs/002-mandi-price-lookup/checklists/security.md (F2 fixed)
tests:
  - 286 passed; live /, /privacy, /terms, /health OK
---

## Prompt

ufone for T008 · show me the demo of interface · deploye it on whatsapp channel · do my work by yourself · do all by yourself only involve me where login required · do all the things to get the app live · how do i get a verified business number · build the website for verification · save all activity of upto today till i resume

## Response snapshot

Recorded Ufone as SMS vendor with the facts Ufone must confirm (inbound/two-way, cross-network reach, callback auth, HTTPS, Urdu `lang`, prices). Published a chat demo from real live replies. Prepared WhatsApp: verify token in Vercel, git-ignored `.env.whatsapp`, `scripts/whatsapp_setup.py`. Browser setup stopped: Meta developer registration is the user's step, then Facebook locked the account (security checkpoint). Added a 10-replies-per-minute cap (finding F2). Explained verified business number steps (portfolio, business verification with SECP/NTN docs, new unregistered number, display name; Meta service-message pricing change 1 Oct 2026). Built and deployed home, privacy policy and terms pages; business details await the user.

## Outcome

- ✅ Impact: app ready for WhatsApp as soon as the user's Meta access works; verification website live
- 🧪 Tests: 286 passing
- 📁 Files: see list
- 🔁 Next prompts: user unlocks Facebook + registers as Meta developer; fills data/business.yaml; optional custom domain
- 🧠 Reflection: account creation, logins and security checkpoints stay with the user even when asked to do everything

## Evaluation notes (flywheel)

- Failure modes observed: sed delimiter clash; Git Bash path conversion in curl output
- Graders run and results (PASS/FAIL): pytest PASS, ruff PASS, mypy PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
