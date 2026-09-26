---
id: 001
title: Mandi price lookup specification
stage: spec
date: 2026-09-26
surface: agent
model: claude-opus-5-5
feature: 002-mandi-price-lookup
branch: 002-mandi-price-lookup
user: hussainbuksh.noorani
command: /sp.specify
labels: ["spec", "mandi-prices", "urdu", "mvp"]
links:
  spec: specs/002-mandi-price-lookup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-mandi-price-lookup/spec.md
  - specs/002-mandi-price-lookup/checklists/requirements.md
tests:
  - none
---

## Prompt

/sp.specify

(Empty description; user selected "Mandi price lookup (Recommended)": Farmer asks the price of a crop at a named mandi in Urdu or Roman Urdu and gets the latest price with its source and date.)

## Response snapshot

Created branch 002-mandi-price-lookup and a spec with three stories: P1 price lookup in Urdu/Roman Urdu with source and date; P2 honest handling of missing/stale data (3-day freshness); P3 one-question clarification. 17 functional requirements, 6 entities, 6 success criteria. Two open clarifications: messaging channel (FR-001) and launch crop/mandi coverage (FR-010).

## Outcome

- ✅ Impact: First chatbot feature specified
- 🧪 Tests: none (spec stage)
- 📁 Files: spec.md, checklists/requirements.md
- 🔁 Next prompts: answer Q1/Q2, then /sp.clarify or /sp.plan
- 🧠 Reflection: create-new-feature.ps1 fails at line 267 on PowerShell 5.1 (3-arg Join-Path); history folder created manually

## Evaluation notes (flywheel)

- Failure modes observed: create-new-feature.ps1 Join-Path incompatibility with Windows PowerShell 5.1
- Graders run and results (PASS/FAIL): spec quality checklist 15/16 PASS (clarifications pending)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): nested Join-Path in create-new-feature.ps1
