---
id: 007
title: Paddy varieties as separate crops
stage: green
date: 2026-09-26
surface: agent
model: claude-opus-5-5
feature: 002-mandi-price-lookup
branch: 002-mandi-price-lookup
user: hussainbuksh.noorani
command: T087
labels: ["reference-data", "dictionary", "fr-010"]
links:
  spec: specs/002-mandi-price-lookup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - data/reference/crops.yaml
  - data/reference/synonyms.yaml
  - src/kisan/understanding/dictionary.py
  - src/kisan/jobs/seed_reference.py
  - tests/unit/test_dictionary.py
  - tests/integration/test_db_seed.py
  - tests/integration/test_fetch_job.py
  - tests/e2e/test_us1_price_lookup.py
  - tests/e2e/test_us3_clarify.py
  - tests/eval/golden.yaml
  - tests/fixtures/sources/fixture/prices.yaml
  - tests/fixtures/sources/amis_punjab/synthetic_normal_day.html
  - specs/002-mandi-price-lookup/{spec,research,tasks}.md
tests:
  - 263 passed; eval 100% ur (39/39) and ur-Latn (43/43); ruff and mypy clean
---

## Prompt

both as separate crops

## Response snapshot

Replaced rice with paddy_basmati and paddy_irri and removed sugarcane. General rice words expand to both varieties; variety words to one; sugarcane words give the "not supported" reply. Source crop labels now match only reviewed exact AMIS labels, so milled rice rows are ignored. Seeding deactivates crops dropped from the reference data. Tests written first (26 failing), then implemented.

## Outcome

- ✅ Impact: FR-010 matches what AMIS actually publishes
- 🧪 Tests: 263 passing
- 📁 Files: see list above
- 🔁 Next prompts: send AMIS permission request; resume /sp.implement at T067
- 🧠 Reflection: exact source-label mapping closes a real risk of showing milled-rice prices as paddy

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): pytest PASS, ruff PASS, mypy PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
