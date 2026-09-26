---
id: 003
title: Kisan Assistant farmer chatbot constitution
stage: constitution
date: 2026-09-26
surface: agent
model: claude-opus-5-5
feature: none
branch: 001-todo-app
user: hussainbuksh.noorani
command: /sp.constitution
labels: ["constitution", "chatbot", "urdu", "agri-finance", "major-version"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - .specify/templates/plan-template.md
  - .specify/templates/tasks-template.md
tests:
  - none
---

## Prompt

/sp.constitution

(Input source: ../Constitution.txt) The concept: a bilingual (Urdu/Roman Urdu) chatbot that farmers text to ask things like "what's the current wheat rate in Multan mandi" or "should I sow cotton now given this week's weather," and it responds using scraped or publicly available mandi price data, weather forecasts, and general agronomic guidance from an LLM. A second layer, drawing on your banking background, could check basic eligibility for common agri-financing schemes (Kisan Card, State Bank agri credit schemes, microfinance) based on landholding size and crop type the farmer describes, and explain in plain language what documents they'd need.

## Response snapshot

Amended the constitution from 1.1.0 to 2.0.0 (MAJOR). Renamed it to Kisan Assistant. Kept Test-First, Tests Define Done, and Simplicity. Redefined Tests at Every Layer (conversation E2E + LLM eval set), Security & Farmer Privacy, and Accessible Low-Bandwidth Conversations. Added Bilingual by Design, Grounded Sourced & Fresh Data, Safe Agronomic Advice, and Indicative-Only Financing Eligibility. Replaced Web Application Constraints with Chatbot & Data Constraints. Updated the plan and tasks templates to match.

## Outcome

- ✅ Impact: Project governance now targets the farmer chatbot domain
- 🧪 Tests: none (governance document)
- 📁 Files: constitution.md, plan-template.md, tasks-template.md
- 🔁 Next prompts: archive specs/001-todo-app; /sp.specify for the mandi price lookup MVP
- 🧠 Reflection: The earlier todo-app spec conflicts with the new scope and was flagged, not deleted

## Evaluation notes (flywheel)

- Failure modes observed: create-phr.sh not present (PowerShell scripts only); PHR written manually
- Graders run and results (PASS/FAIL): placeholder check PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
