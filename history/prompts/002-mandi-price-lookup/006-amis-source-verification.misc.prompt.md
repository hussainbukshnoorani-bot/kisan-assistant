---
id: 006
title: AMIS source verification T007
stage: misc
date: 2026-09-26
surface: agent
model: claude-opus-5-5
feature: 002-mandi-price-lookup
branch: 002-mandi-price-lookup
user: hussainbuksh.noorani
command: T007
labels: ["verification", "data-source", "amis", "principle-ix"]
links:
  spec: specs/002-mandi-price-lookup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-mandi-price-lookup/research.md
  - specs/002-mandi-price-lookup/spec.md
  - specs/002-mandi-price-lookup/tasks.md
tests:
  - none
---

## Prompt

T007

## Response snapshot

Checked amis.pk by hand (7 page views, 3 s apart). robots.txt is 404; no terms page; footer says "All rights reserved", so permission is not confirmed and the source stays disabled; the user needs to request written permission or a data feed from the Directorate of Agriculture (E&M) Punjab. Prices are per city page, Rs/100Kg, dated daily, "-" for missing; city IDs 1 Lahore, 2 Faisalabad, 4 Okara, 6 Rawalpindi, 7 Multan. No farm sugarcane price, so sugarcane dropped from FR-010; rice is split into Paddy Basmati/IRRI (decision needed). Added T087.

## Outcome

- ✅ Impact: T007 facts recorded; permission is the remaining blocker
- 🧪 Tests: none
- 📁 Files: research.md (R6 verification), spec.md (FR-010), tasks.md (T007 note, T087)
- 🔁 Next prompts: send the permission request; T087; rework connector on real pages after permission
- 🧠 Reflection: the real layout differs a lot from the synthetic sample pages

## Evaluation notes (flywheel)

- Failure modes observed: WebFetch forces HTTPS and the site is HTTP-only; used curl
- Graders run and results (PASS/FAIL): n/a
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
