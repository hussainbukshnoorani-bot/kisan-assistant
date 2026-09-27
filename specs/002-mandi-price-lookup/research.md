# Research: Mandi Price Lookup

**Feature**: `002-mandi-price-lookup` | **Date**: 2026-09-26

Each entry records the decision, why it was made, and what else was considered. Items marked
**VERIFY** are decisions that depend on an external fact that must be confirmed before the
related implementation task starts; each has a matching blocking task in `tasks.md`.

---

## R1. Language and web framework

- **Decision**: Python 3.11 with FastAPI (ASGI) served by Uvicorn.
- **Rationale**: Python 3.11 is already installed on the development machine; Python has the
  strongest ecosystem for scraping (httpx, selectolax), fuzzy text matching (rapidfuzz), and
  LLM SDKs. FastAPI gives typed request models (Pydantic) that double as webhook contracts, and
  background tasks for the "checking…" holding message.
- **Alternatives considered**: Node.js/TypeScript (also installed; good WhatsApp libraries, but
  weaker text-matching and scraping tooling); Django (heavier than needed — no admin UI or ORM
  features are required by this feature).

## R2. Storage

- **Decision**: PostgreSQL 16 for crops, mandis, synonyms, price records, pending
  clarifications, and conversation turns. SQLAlchemy 2.0 + Alembic migrations.
- **Rationale**: One store covers reference data, time-stamped prices, and short-lived
  conversation state (30-minute pending clarification, FR-009) via an `expires_at` column.
- **Alternatives considered**: Redis for session state (rejected under Principle V — a second
  datastore for a single 30-minute timer is not justified); SQLite (fine for development, but
  concurrent webhook writes and managed hosting favour Postgres). Tests use Postgres in a
  container, not SQLite, so behaviour matches production.

## R3. WhatsApp channel

- **Decision**: Meta WhatsApp Cloud API. Inbound messages arrive at `POST /webhooks/whatsapp`;
  subscription verification at `GET /webhooks/whatsapp` (hub.challenge). Every POST is
  authenticated by checking `X-Hub-Signature-256` (HMAC-SHA256 of the raw body with the app
  secret) before parsing.
- **Rationale**: Official API, no third-party intermediary holding farmer messages, and every
  reply in this feature is a response inside the 24-hour customer-service window, so no
  pre-approved templates are needed (spec Assumption).
- **Alternatives considered**: Twilio WhatsApp (adds a per-message markup and another processor
  of personal data); unofficial WhatsApp Web libraries (violate WhatsApp terms and get numbers
  banned).

## R4. SMS channel

- **Decision**: A Pakistani SMS aggregator offering a two-way shortcode or long code, reached
  through a thin `SmsProvider` adapter. The adapter converts the provider's inbound callback into
  the internal `InboundMessage` contract and sends replies through the provider's HTTP API.
  Inbound callbacks are authenticated with a shared secret in the callback URL path or header
  (whichever the provider supports), compared in constant time.
- **VERIFY**: Vendor selection and contract (two-way support, Urdu/UCS-2 delivery, callback
  authentication method, cost per segment) is a procurement step outside the codebase. Until a
  vendor is chosen, development and all tests use the recorded-fixture fake provider.
- **T008 decision (2026-09-27): Ufone** (user's choice). Public information found:
  - **Outbound — Ufone Business SMS (BSMS) HTTP API.** No official public docs; described by
    unofficial copies of the spec (BSMS API v0.3/v0.8 on Scribd) and a community PHP wrapper
    (github.com/asimzeeshan/UfoneBusinessSMSAPI): HTTP `GET` to a `bsms.ufone.com` JSP endpoint
    with parameters `id` (sender MSISDN), `message`, `shortcode`, `lang`, `password`,
    `mobilenum` (92XXXXXXXXXX); XML response with `response_id` 0 = sent, 1 = failed. Urdu is
    supported ("English-Urdu"), selected via `lang` — exact value undocumented.
  - **Inbound (two-way) — not documented.** BSMS is described as outbound only; receiving
    farmers' messages needs a Ufone short code / MO arrangement agreed commercially.
  - **Must be confirmed with Ufone in writing before T076** (the adapter is not built on the
    unofficial spec): (1) inbound short code or long number with an HTTP callback (MO)
    to our webhook, its payload fields and how it is authenticated (header secret or
    signature preferred — see security finding F1); (2) whether farmers on **Jazz, Telenor
    and Zong** can reach that number, or only Ufone subscribers (a Ufone-only number would
    exclude most farmers); (3) the current official send API (HTTPS? the unofficial one is
    plain HTTP with the password in the URL), the `lang` value for Urdu, and UCS-2
    concatenation up to 2 segments; (4) delivery receipts; (5) price per segment for Urdu
    and English, and short-code rental.
  - If Ufone cannot offer cross-network inbound, use an aggregator that connects Ufone plus
    the other three networks to one short code, keeping Ufone for outbound if cheaper.
- **Rationale**: International providers generally cannot offer inbound two-way numbers in
  Pakistan; local aggregators with PTA-registered shortcodes are the normal route.
- **Alternatives considered**: Twilio SMS (outbound to Pakistan is possible, but two-way inbound
  numbers are not generally available there); a GSM modem/SIM gateway (unreliable, and bulk use of
  consumer SIMs can breach operator terms).

## R5. SMS length budget (FR-001a)

- **Decision**: SMS replies are limited to 2 segments: 306 characters for GSM-7 text (Roman
  Urdu) and 134 characters for UCS-2 text (Urdu script) when concatenated (153 × 2 and 67 × 2).
  The reply renderer has one compact SMS template per reply type; required fields from FR-005
  are never dropped, optional text (greeting, "ask again later" hints) is dropped first. A unit
  test asserts every SMS template, filled with the longest crop/mandi names, fits the budget.
- **Rationale**: Urdu script forces UCS-2 encoding, which cuts capacity to less than half; a
  fixed budget per encoding makes the limit testable. Roman Urdu SMS templates use only GSM-7
  characters (plain hyphen for ranges); one non-GSM character would force UCS-2 and the 134
  budget. On SMS, multi-pair questions get as many pairs as fit (at least 1), then a "send the
  rest separately" line.
- **Alternatives considered**: Single-segment SMS (too short for Urdu script with source and
  date); unlimited segments (cost and delivery reliability suffer on basic phones).

## R6. Price data source

- **Decision**: Primary source is the Punjab Agriculture Marketing Information Service (AMIS,
  amis.pk), which publishes daily commodity prices for Punjab markets. A `PriceSource`
  connector fetches and parses the published pages/files on a schedule and normalizes them into
  `PriceRecord`s (see `contracts/price-source.md`).
- **VERIFY (blocking, Principle IX)**: Before the first live fetch, confirm and record in this
  file: (a) the site's terms of use / robots.txt allow automated retrieval, (b) that all 5
  launch crops and 10 launch mandis are published, (c) the publishing time and frequency, and
  (d) the unit used. If terms do not permit scraping, request written permission or a data feed
  from the publisher; the feature does not go live on an unpermitted source.
- **Known risk**: Sugarcane is mostly sold directly to mills at a government-notified price, so
  mandi prices for it may be sparse. If (b) shows no sugarcane mandi data, sugarcane is dropped
  from FR-010 (or replaced by another crop) via a spec amendment rather than filled from another
  kind of price.
- **R6 verification (T007, checked 2026-09-26 by hand: 7 page views, 3 s apart)**:
  - **(a) Permission — NOT CONFIRMED.** `http://www.amis.pk/robots.txt` returns 404 (no
    robots restrictions). There is no terms-of-use or data-use page; the only statement is the
    footer: "Copyright © 2006-2026 Agriculture Marketing Information Service(AMIS), Directorate
    of Agriculture (Economics & Marketing) Punjab, Lahore. All rights reserved." "All rights
    reserved" is not permission, so under Principle IX the source stays disabled. **Next step:**
    ask the publisher in writing for permission or a data feed — Directorate of Agriculture
    (E&M) Punjab, 21-Davis Road, Lahore, tel +92-42-99201094, fax +92-42-99203927. The site links
    an official Android app built by PITB (`pitb.gov.pk.amis`), so a data feed/API may exist;
    ask about it in the same request. Site is HTTP only (no HTTPS).
  - **(b) Coverage — partial.** Prices are published per city on
    `ViewPrices.aspx?searchType=1&commodityId=<cityId>` (the parameter is named commodityId but
    selects the city). Confirmed IDs: 1 Lahore, 2 Faisalabad, 4 Okara, 6 Rawalpindi, 7 Multan;
    IDs for Gujranwala, Sahiwal, Bahawalpur, Sargodha, Rahim Yar Khan not yet found (the city
    list loads by script). Rows seen: Wheat, Maize, Seed Cotton (Phutti), Paddy Basmati,
    Paddy (IRRI), Rice varieties. On 26 Sep 2026 many cells were "-" (no price): wheat at
    Lahore, Okara, Multan; phutti and paddy at all five cities; wheat and maize had prices at
    Faisalabad and Rawalpindi, maize at Okara and Multan. Expect seasonal gaps (US2 handles them).
    **Sugarcane:** no farm sugarcane row; the only match is "sugarcane (گنڈیری)", peeled cane sold
    as a snack in fruit and vegetable markets — not the farmer's crop. Per the known risk below,
    sugarcane is dropped from FR-010.
    **Rice:** AMIS lists paddy by variety (Basmati, IRRI); decided 2026-09-26 to offer both as
    separate crops (`paddy_basmati`, `paddy_irri`). Source crop labels are matched exactly via
    `source_labels` in synonyms.yaml, so milled rice rows ("Rice Basmati Super") are ignored.
  - **(c) Publishing:** each page shows "Dated:dd-mm-yyyy" in its header (26-09-2026 on the day
    checked), i.e. daily; the exact upload time is not shown on the page.
  - **(d) Units:** "All Prices are in Rs/100Kg specified otherwise"; columns are Min, Max, FQP
    (fair average quality price) and Quantity; "-" means no price. Example: Faisalabad wheat
    Rs 11,500–12,000 per 100 kg = Rs 4,600–4,800 per 40 kg.
  - **Connector impact:** the real layout differs from the synthetic fixtures (one page per
    city; date in the page header, not per row; unit given once for the page; commodity rows
    grouped under category headings). `amis_punjab.py` must be reworked against recorded real
    pages (T009) once permission is granted. Pages were not saved as fixtures because retrieval
    permission is not yet confirmed.
- **Rationale**: A single official provincial source covers the launch scope and keeps
  provenance simple (one source name in every reply).
- **Alternatives considered**: PBS weekly Sensitive Price Indicator (consumer retail prices,
  not mandi prices — wrong for farmers); crowdsourced prices from traders (unverifiable at
  launch).

## R7. Fetch schedule and freshness

- **Decision**: A fetch job (`python -m kisan.jobs.fetch_prices`) runs every 2 hours from 06:00
  to 20:00 PKT, triggered by the host's scheduler (cron or platform scheduled job). Requests are
  rate-limited to 1 per 2 seconds with an identifying User-Agent. A price is current if its
  price date is within 3 calendar days of today in Asia/Karachi time (FR-006).
- **Rationale**: Mandi rates are published once a day; a few fetches per day catch late updates
  without load on the publisher. A scheduled CLI job needs no in-process scheduler.
- **Alternatives considered**: Fetch on each farmer request (slow, hammers the source, and fails
  the 10 s budget if the source is slow); APScheduler inside the web process (runs N times when
  scaled to N instances).

## R8. Understanding messages (crop / mandi extraction)

- **Decision**: Two-stage extraction.
  1. **Deterministic stage**: normalise text (Unicode NFKC, Urdu character variants such as
     ي/ی and ك/ک, lowercase Roman Urdu, strip punctuation), detect script, then match tokens
     against the synonym dictionary with rapidfuzz (score ≥ 88 for Roman Urdu, exact after
     normalisation for Urdu script).
  2. **LLM fallback**: only when stage 1 finds neither crop nor mandi, or is ambiguous, call
     `claude-haiku-4-5` with a versioned prompt that must return JSON matching
     `contracts/llm-extraction.schema.json` (IDs chosen from the supplied dictionary list, or
     null). The output is validated against the schema and the dictionary; anything else is
     discarded and treated as "not understood".
- **Rationale**: The dictionary handles most messages in milliseconds at no cost and is fully
  testable; the LLM covers free-form phrasing and heavy misspellings, which SC-002 (90%
  understood) needs. The LLM never produces prices or reply text — it only picks IDs — so
  Principle IX holds by construction.
- **Alternatives considered**: Dictionary only (likely below 90% on real Roman Urdu; the eval
  set will measure this, and the LLM stage can be removed if the dictionary alone passes);
  LLM-only (slower, costlier, and harder to make deterministic in tests); a trained intent model
  (no labelled data yet).
- **T067 result (2026-09-27)**: dictionary-only pass rate on the golden set is 100% for both
  scripts (Urdu script 39/39, Roman Urdu 43/43), above the 90% gate, so the LLM fallback
  (T068, T070–T072) is **not built** for now and the `anthropic` dependency stays unused.
  Caveat: the golden set was written by the developer, not by farmers or native speakers.
  Re-run this gate after the native-speaker review (T077) and the pilot (T085); if either
  script drops below 90%, build the fallback as planned.

## R9. Reply generation

- **Decision**: All replies are rendered from a reviewed translation catalogue
  (`catalogue/ur.yaml` for Urdu script, `catalogue/ur-Latn.yaml` for Roman Urdu), one template
  per reply type and channel (WhatsApp / SMS). Numbers are formatted with thousands separators
  and Western digits; dates as "26 Sep" / "26 ستمبر".
- **Rationale**: Principle VIII requires reviewed, non-hardcoded strings; templates make reply
  length and required fields unit-testable (FR-005, FR-012, FR-001a).
- **Alternatives considered**: LLM-written replies (risk of altered numbers, harder to review,
  violates Principle IX spirit).

## R10. Script detection

- **Decision**: A message is "Urdu script" if more than 50% of its letters are in the Arabic
  Unicode block, otherwise "Roman Urdu". The reply uses the detected script (FR-003, mixed-text
  edge case). English-only messages are answered in Roman Urdu.
- **Rationale**: Simple, deterministic, and matches the spec's "majority script" rule.

## R11. Holding message and reply time (FR-013)

- **Decision**: The webhook handler acknowledges the provider immediately (HTTP 200) and handles
  the message in a background task. If the answer is not ready after 5 s, a catalogue "checking…"
  message is sent; the task gives up at 9 s and sends the "can't fetch prices now" reply.
  Price lookups read from Postgres (pre-fetched by R7), so the normal path takes well under 1 s;
  only the LLM fallback can approach the limit, and it has a 4 s timeout.
- **Rationale**: Meets median < 5 s / p95 < 10 s and keeps provider webhooks from retrying.
  The `source_down` reply is sent when the price database cannot be read or the 9 s cutoff is
  hit; a failed collection run never triggers it (prices are simply stale or missing).
- **Repeat deliveries (FR-019)**: `ConversationTurn.provider_message_id` is unique per channel;
  the handler inserts the turn first and drops the message if the insert conflicts.

## R12. Privacy (Principle IV)

- **Decision**: Phone numbers are never stored in plain text. The contact is stored as
  `contact_hash = HMAC-SHA256(secret_pepper, channel + ":" + E.164 number)`; the raw number is
  only held in memory for the duration of the reply. Message text in conversation turns is
  stored for 90 days (for traceability and eval-set building), then deleted by a daily purge job.
  Logs record `contact_hash` and conversation ID, never the number or full message text.
  The LLM prompt receives only the message text, never the phone number.
- **Redaction (FR-018)**: Before message text is stored, logged, or sent to the LLM, CNIC patterns
  (`\d{5}-?\d{7}-?\d`) and Pakistani phone patterns (`+92` / `92` / `0` followed by `3\d{9}`,
  with optional spaces or dashes) are replaced with `[CNIC]` and `[PHONE]`. Urdu-script digits
  (۰–۹) are normalised to ASCII before matching.
- **Rationale**: The feature needs no personal data (FR-014); hashing still allows the 30-minute
  clarification state and per-farmer metrics (SC-005).
- **Alternatives considered**: Encrypting numbers at rest (unnecessary — the number is never
  needed after the reply is sent).

## R13. Prompt injection (Principle IV)

- **Decision**: The LLM is only asked to choose IDs from a supplied list and must return
  schema-valid JSON; any output that does not validate is discarded. Farmer text is wrapped in a
  delimited block and the system prompt states it is data, not instructions. Because replies come
  from templates and prices from the database, a successful injection can at worst cause a
  "not understood" reply. Eval set includes injection attempts.

## R14. Testing stack

- **Decision**: pytest, pytest-asyncio, httpx `AsyncClient` for webhook tests, respx for stubbing
  outbound HTTP (WhatsApp send, SMS send, AMIS fetch, Anthropic API), pgserver (local) or a CI Postgres service for
  Postgres (R17), recorded HTML/JSON fixtures of the price source, `time-machine` for freezing
  Asia/Karachi time, coverage.py with an 80% gate on changed code, pip-audit for dependency
  scanning.
- **Eval set**: `tests/eval/golden.yaml` — at least 100 questions (≥ 50 Urdu script, ≥ 50 Roman
  Urdu) written with native-speaker review, each with expected crop ID, mandi ID, or expected
  reply type, plus forbidden outputs. CI runs it with the LLM stubbed by recorded responses;
  a nightly job runs it against the live model and fails if the pass rate drops.

## R15. Observability (Principle VI)

- **Decision**: structlog JSON logs with `conversation_id`, `contact_hash`, `channel`,
  `reply_type`, `price_record_ids`, `prompt_version`, `model`, and latency. Sentry (or equivalent)
  for unhandled errors with PII scrubbing. `GET /health` checks the database and reports the age
  of the newest price record; the fetch job logs per-source success/failure and raises an alert
  when a source fails 3 runs in a row or returns no records.

## R16. Hosting

- **Decision**: One Docker image running the FastAPI app, plus the scheduled fetch and purge jobs
  using the same image; managed PostgreSQL. The specific host is left to deployment and does not
  affect the design.

## R17. Test database without Docker

- **Decision**: Local test runs use the `pgserver` package, which bundles PostgreSQL binaries and
  starts a throwaway server per test session. If `TEST_DATABASE_URL` is set (e.g. in CI with a
  Postgres service container), tests use that instead.
- **Rationale**: Docker and PostgreSQL are not installed on the development machine (2026-09-26);
  pgserver keeps tests on real PostgreSQL rather than SQLite.
