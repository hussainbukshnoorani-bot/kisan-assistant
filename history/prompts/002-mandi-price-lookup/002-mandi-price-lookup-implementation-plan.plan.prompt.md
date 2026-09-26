---
id: 002
title: Mandi price lookup implementation plan
stage: plan
date: 2026-09-26
surface: agent
model: claude-opus-5-5
feature: 002-mandi-price-lookup
branch: 002-mandi-price-lookup
user: hussainbuksh.noorani
command: /sp.plan
labels: ["plan", "fastapi", "postgres", "whatsapp", "sms", "urdu"]
links:
  spec: specs/002-mandi-price-lookup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-mandi-price-lookup/plan.md
  - specs/002-mandi-price-lookup/research.md
  - specs/002-mandi-price-lookup/data-model.md
  - specs/002-mandi-price-lookup/quickstart.md
  - specs/002-mandi-price-lookup/contracts/webhooks.openapi.yaml
  - specs/002-mandi-price-lookup/contracts/price-source.md
  - specs/002-mandi-price-lookup/contracts/llm-extraction.schema.json
  - specs/002-mandi-price-lookup/spec.md
  - CLAUDE.md
tests:
  - none
---

## Prompt

/sp.plan

(Q2 on launch coverage was not answered; recommended default Option A applied to FR-010.)

## Response snapshot

Planned a single Python 3.11/FastAPI service with PostgreSQL. WhatsApp Cloud API plus an SMS aggregator adapter (fake provider until a vendor is chosen). Crop/mandi extraction uses a normalising synonym dictionary with a claude-haiku-4-5 fallback that may only return dictionary IDs. Replies come from reviewed Urdu/Roman Urdu templates with per-channel length budgets (SMS: 306 GSM-7 / 134 UCS-2 chars). Prices are pre-fetched from AMIS Punjab every 2 hours and validated; current means 3 days or newer. Phone numbers are stored only as HMAC hashes. Constitution Check v2.0.0 passes; the LLM fallback and dual channels are justified in Complexity Tracking.

## Outcome

- ✅ Impact: Design artifacts ready for /sp.tasks
- 🧪 Tests: none (plan stage)
- 📁 Files: plan, research, data model, quickstart, 3 contracts; spec FR-010 default; CLAUDE.md tech lines
- 🔁 Next prompts: /sp.tasks
- 🧠 Reflection: AMIS terms/coverage and the SMS vendor are external facts that must be verified; they are gated by blocking tasks rather than assumed

## Evaluation notes (flywheel)

- Failure modes observed: update-agent-context.ps1 reads only the first line of a wrapped Technical Context field (fixed CLAUDE.md by hand); a long multi-heredoc bash command failed to parse and was replaced with separate file writes
- Graders run and results (PASS/FAIL): Constitution Check PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): keep Technical Context fields on one line so the agent-context script parses them fully
