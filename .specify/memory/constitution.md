<!--
Sync Impact Report
- Version change: 1.1.0 → 2.0.0 (MAJOR: project scope redefined from a generic web app to the
  Kisan Assistant bilingual farmer chatbot; principles II, IV, VII and the constraints section
  redefined in backward-incompatible ways)
- Modified principles:
  - II. Tests at Every Layer → II. Tests at Every Layer (E2E now = conversation flows; LLM
    output evaluated with a golden-question eval set)
  - IV. Security by Default → IV. Security & Farmer Privacy (adds PII minimization for phone
    numbers, CNIC, landholding data)
  - VII. Accessibility & Performance → VII. Accessible, Low-Bandwidth Conversations (WCAG
    budgets replaced by messaging-channel and low-literacy rules)
- Added sections:
  - VIII. Bilingual by Design (Urdu / Roman Urdu)
  - IX. Grounded, Sourced & Fresh Data
  - X. Safe Agronomic Advice
  - XI. Financing Eligibility Is Indicative, Never a Decision
  - Chatbot & Data Constraints (replaces Web Application Constraints)
- Removed sections: Web Application Constraints (superseded)
- Templates:
  - ✅ .specify/templates/plan-template.md (Constitution Check gates updated for II, IV, VII–XI)
  - ✅ .specify/templates/tasks-template.md (foundational + polish tasks updated)
  - ✅ .specify/templates/spec-template.md (no change needed; success criteria already mandatory)
- Follow-up:
  - ⚠ specs/001-todo-app/ was written under v1.1.0 and does not match the new project scope;
    archive or delete it before starting the first chatbot feature.
- Deferred TODOs: none
-->

# Kisan Assistant Constitution

A bilingual (Urdu / Roman Urdu) chatbot that Pakistani farmers message to ask about mandi
prices, weather-informed sowing decisions, and general agronomy, with a second layer that
checks indicative eligibility for agri-financing schemes (Kisan Card, State Bank of Pakistan
agri-credit schemes, microfinance) and explains the documents required.

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

All production code MUST be written using Test-Driven Development:

- A failing test MUST exist before any implementation code is written for a behavior.
- The Red → Green → Refactor cycle MUST be followed: write a failing test, write the minimum
  code to make it pass, then refactor with all tests green.
- Tests MUST be observed failing for the expected reason before implementation begins.
- Bug fixes MUST start with a test that reproduces the bug.

**Rationale**: Writing tests first forces clear requirements, keeps designs testable, and
prevents untested code from reaching the codebase.

### II. Tests at Every Layer

- **Unit tests** for intent parsing, entity extraction (crop, mandi/city, quantity, land
  size), price normalization, and eligibility rules.
- **Contract / integration tests** for every external boundary: messaging webhook, price
  sources/scrapers, weather API, and LLM provider. External services MUST be stubbed with
  recorded fixtures; tests MUST NOT call live services.
- **End-to-end conversation tests** for every P1 user journey, driving the bot through the
  messaging webhook with realistic Urdu and Roman Urdu messages.
- **LLM evaluation set**: a versioned golden set of farmer questions with expected facts and
  forbidden outputs MUST run in CI; a prompt or model change MUST NOT reduce its pass rate.
- Tests MUST be deterministic: no dependence on test order, live data, or uncontrolled time.

**Rationale**: LLM behavior and scraped data drift silently; only fixtures and an eval set make
regressions visible.

### III. Tests Define "Done"

- A task is complete only when its tests pass locally and in CI.
- Every acceptance scenario in a spec MUST map to at least one automated test.
- The full test suite MUST pass before any merge to the main branch; failing or skipped tests
  MUST NOT be merged without a linked issue and justification.
- Coverage of new/changed code MUST be at least 80% lines; coverage MUST NOT decrease on merge.

**Rationale**: Making tests the definition of done keeps the TDD discipline enforceable rather
than aspirational.

### IV. Security & Farmer Privacy

- Collect only the data a feature needs. Phone numbers, CNIC numbers, landholding details, and
  income information are personal data: they MUST be encrypted at rest, MUST NOT appear in
  logs or LLM prompts unless strictly required, and MUST have a defined retention period.
- The bot MUST NOT ask for passwords, PINs, OTPs, or full bank account/card numbers, ever.
- Webhooks MUST verify the messaging provider's signature; admin endpoints MUST require
  authentication and authorization covered by allowed/denied tests.
- LLM inputs MUST be treated as untrusted: prompt-injection attempts in user messages MUST NOT
  be able to change system instructions, reveal secrets, or bypass Principles IX–XI.
- Dependencies MUST be scanned in CI; high/critical findings block merge unless an issue with a
  remediation date is linked. Secrets MUST never appear in code, logs, or responses.

**Rationale**: Farmers are a target for financial fraud; a bot that normalizes sharing
sensitive details would put them at risk.

### V. Simplicity (YAGNI)

- Build only what the current spec requires; speculative features, configuration options, and
  abstractions MUST NOT be added "for later".
- Prefer the smallest viable change; do not refactor unrelated code in a feature change.
- A new dependency, service, layer, or pattern (e.g. vector store, queue, agent framework)
  MUST be justified in the plan's Complexity Tracking table with the simpler alternative it
  replaces.

**Rationale**: Every abstraction has a maintenance cost; complexity must earn its place by
solving a present, stated problem.

### VI. Observability

- Services MUST emit structured (JSON) logs with level, timestamp, and a conversation/
  correlation ID propagated across webhook → orchestration → data sources → LLM.
- Each answer MUST be traceable to the data sources, fetch timestamps, prompt version, and
  model that produced it.
- Scraper and data-source failures MUST raise alerts; unhandled errors MUST be captured with
  enough context to reproduce and MUST NOT leak internals to the farmer.
- Each deployable service MUST expose a health check endpoint. Logs MUST honor Principle IV.

**Rationale**: When a farmer receives a wrong price, we must be able to find out exactly why.

### VII. Accessible, Low-Bandwidth Conversations

- Replies MUST be short, plain-language, and readable on a basic phone: default ≤ 480
  characters, no reliance on images, links, or rich formatting to convey essential content.
- Replies MUST avoid jargon; units MUST be ones farmers use (e.g. per 40 kg / maund, acres).
- Median end-to-end reply time MUST be < 5 s and p95 < 10 s; if a source is slow, the bot MUST
  send a brief holding reply rather than stay silent.
- The bot MUST handle spelling variants, mixed-script messages, and ambiguous questions by
  asking one short clarifying question instead of guessing.

**Rationale**: Users may have limited literacy, patchy connectivity, and inexpensive phones;
an accurate answer they cannot read or receive has no value.

### VIII. Bilingual by Design (Urdu / Roman Urdu)

- The bot MUST understand and reply in Urdu script and Roman Urdu, and MUST reply in the script
  the farmer used unless they ask otherwise.
- All user-facing text that is not LLM-generated MUST come from a translation catalogue
  reviewed by a fluent Urdu speaker; hard-coded user-facing strings are not allowed.
- Crop, mandi, and city names MUST be resolved through a maintained synonym dictionary covering
  Urdu, Roman Urdu, and English spellings.
- The eval set (Principle II) MUST include questions in both scripts for every P1 journey.

**Rationale**: Language is the product; English-first design with translation bolted on fails
the people this bot is built for.

### IX. Grounded, Sourced & Fresh Data

- Prices and weather figures MUST come from retrieved data, never from LLM generation. If no
  data is available, the bot MUST say so; it MUST NOT estimate or invent a figure.
- Every price or forecast reply MUST state its source and date (e.g. "Multan mandi, 26 Sep").
- Each data source MUST define a freshness limit in its spec; data older than that limit MUST
  be flagged as stale in the reply or withheld.
- Only publicly available sources whose terms permit use MAY be scraped; scrapers MUST respect
  robots.txt and rate limits, and each source's terms MUST be recorded in the plan.

**Rationale**: Farmers make selling and sowing decisions with real money on these numbers; a
confident wrong price is worse than no answer.

### X. Safe Agronomic Advice

- Agronomic guidance MUST be framed as general guidance, not a guarantee, and MUST combine
  retrieved weather/season data with the LLM rather than rely on the LLM alone.
- The bot MUST NOT recommend specific pesticide or chemical dosages beyond what an approved
  reference source states, and MUST direct farmers to the local agriculture extension office
  for pest outbreaks, disease, or other high-risk decisions.
- Answers outside the bot's scope (medical, legal, non-agricultural) MUST be declined politely
  with a pointer to an appropriate human source.

**Rationale**: Wrong sowing or spraying advice can destroy a season's income or harm health.

### XI. Financing Eligibility Is Indicative, Never a Decision

- Eligibility checks MUST be implemented as deterministic, versioned rules (landholding size,
  crop type, scheme criteria) with unit tests. The LLM MAY explain results but MUST NOT decide
  eligibility.
- Every rule set MUST cite its official source document and effective date; rules MUST be
  reviewed when a scheme changes.
- Every eligibility reply MUST state that the result is indicative only, that the bank or
  lender makes the final decision, and list the required documents.
- The bot MUST NOT collect loan applications, promise approval, or recommend a specific lender.

**Rationale**: Bank schemes change and approval depends on factors the bot cannot see;
presenting a guess as a decision would mislead farmers financially.

## Chatbot & Data Constraints

- The system MUST separate the messaging channel adapter, conversation orchestration, data
  source connectors, eligibility rules engine, and LLM client so each can be tested in
  isolation (Principle II).
- Every external boundary (webhook payloads, source connectors, LLM prompts/outputs) MUST have
  a defined schema or contract before implementation, with contract tests written first.
- Prompts MUST be versioned files, not inline strings, and changes MUST run the eval set.
- Configuration and credentials MUST come from environment variables; nothing sensitive is
  committed.

## Development Workflow & Quality Gates

1. `/sp.specify` → spec with prioritized user stories, acceptance scenarios, and sample farmer
   messages in both scripts.
2. `/sp.plan` → plan MUST pass the Constitution Check (data sources, freshness limits, and test
   strategy per layer defined).
3. `/sp.tasks` → for each user story, test tasks MUST appear before implementation tasks.
4. `/sp.implement` → execute tasks in Red → Green → Refactor order.
5. Before merge: all tests green, coverage gate met, eval set pass rate not reduced, dependency
   scan clean, and code reviewed for constitution compliance.

## Governance

- This constitution supersedes all other development practices for this project.
- Amendments MUST be made via `/sp.constitution`, documented in the Sync Impact Report, and
  versioned using semantic versioning:
  - MAJOR: principle removed or redefined in a backward-incompatible way.
  - MINOR: new principle or section added, or guidance materially expanded.
  - PATCH: clarifications and wording fixes.
- Every plan and code review MUST verify compliance with these principles. Any deviation MUST
  be recorded in the plan's Complexity Tracking table with justification.

**Version**: 2.0.0 | **Ratified**: 2026-09-26 | **Last Amended**: 2026-09-26
