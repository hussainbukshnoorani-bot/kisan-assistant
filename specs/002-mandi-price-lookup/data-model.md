# Data Model: Mandi Price Lookup

**Feature**: `002-mandi-price-lookup` | **Date**: 2026-09-26

All timestamps are stored in UTC (`timestamptz`); "today" and price dates are evaluated in
`Asia/Karachi`. No table stores a phone number (research R12).

## Reference data

### Crop

| Field | Type | Rules |
|-------|------|-------|
| id | text, PK | Stable slug, e.g. `wheat`, `cotton`, `rice`, `sugarcane`, `maize` |
| name_ur | text | Display name in Urdu script, e.g. گندم |
| name_ur_latn | text | Display name in Roman Urdu, e.g. Gandum |
| name_en | text | English name |
| min_plausible_rs_40kg | integer | > 0; prices below are rejected (FR-015) |
| max_plausible_rs_40kg | integer | > min; prices above are rejected (FR-015) |
| active | boolean | Only active crops are answered and listed (FR-011) |

### Mandi

| Field | Type | Rules |
|-------|------|-------|
| id | text, PK | Slug, e.g. `multan` |
| name_ur, name_ur_latn, name_en | text | Display names |
| district | text | Informational |
| neighbours | text[] | Reviewed list of neighbouring mandi IDs for the FR-008 fallback, in preference order |
| province | text | `punjab` at launch |
| active | boolean | |

### Synonym

Maps every accepted spelling to a crop or mandi (Principle VIII).

| Field | Type | Rules |
|-------|------|-------|
| id | bigint, PK | |
| entity_type | enum `crop` / `mandi` | |
| entity_id | text | FK to Crop.id or Mandi.id |
| script | enum `ur` / `ur-Latn` / `en` | |
| text_normalized | text | Output of the normaliser (R8); unique per (entity_type, text_normalized) |

Seed data (crops, mandis, synonyms) lives in versioned YAML under `data/reference/` and is
loaded by a migration/seed command, so reference changes are reviewed in pull requests.

### PriceSource

| Field | Type | Rules |
|-------|------|-------|
| id | text, PK | e.g. `amis_punjab` |
| display_name_ur, display_name_ur_latn | text | Shown in replies (FR-005) |
| url | text | |
| terms_note | text | Required, non-empty before the source is enabled (FR-017, R6) |
| terms_verified_on | date | Required before `enabled = true` |
| enabled | boolean | Fetch job skips disabled sources |

## Price data

### PriceRecord

| Field | Type | Rules |
|-------|------|-------|
| id | bigint, PK | |
| source_id | text, FK → PriceSource | |
| crop_id | text, FK → Crop | |
| mandi_id | text, FK → Mandi | |
| price_date | date | Date the price applies to (as published) |
| min_rs_40kg | integer, nullable | Converted to Rs per 40 kg |
| max_rs_40kg | integer, nullable | ≥ min when both present; at least one of min/max required |
| original_unit | text | Unit as published, e.g. `per_40kg`, `per_100kg` |
| fetched_at | timestamptz | When the connector retrieved it (FR-016) |
| status | enum `valid` / `rejected` | `rejected` when outside plausible range, zero, or negative |
| reject_reason | text, nullable | Required when `status = rejected` |

- Unique on (source_id, crop_id, mandi_id, price_date); a re-fetch with changed values updates
  the row and `fetched_at`.
- Only `valid` rows are ever read for replies.
- **Currentness** (derived, not stored): current if `today_pkt - price_date ≤ 3 days` (FR-006).

## Conversation data

### PendingClarification

Holds a half-understood question for FR-009 / User Story 3.

| Field | Type | Rules |
|-------|------|-------|
| contact_hash | text, PK part | HMAC of channel + number (R12) |
| channel | enum `whatsapp` / `sms` | PK part — channels never share state (spec edge case) |
| crop_id | text, nullable | What was already understood |
| mandi_id | text, nullable | |
| awaiting | enum `crop` / `mandi` | What the bot asked for |
| created_at | timestamptz | |
| script | enum `ur` / `ur-Latn` | |
| expires_at | timestamptz | created_at + 30 minutes |

State transitions:

```text
(none) --message missing crop or mandi--> Pending(awaiting=X)
Pending --reply supplies X within 30 min--> answered --> (deleted)
Pending --reply is a complete new question--> answered with new question --> (deleted)
Pending --30 min pass--> expired (ignored, purged)
```

### ConversationTurn

One inbound message and its reply, for traceability (FR-016, Principle VI).

| Field | Type | Rules |
|-------|------|-------|
| id | uuid, PK | Also the `conversation_id` in logs |
| provider_message_id | text | Unique per channel; a repeat delivery is ignored (FR-019) |
| contact_hash | text | |
| channel | enum | |
| received_at | timestamptz | |
| message_text | text | CNIC and phone numbers replaced with `[CNIC]` / `[PHONE]` before storage (FR-018); deleted after 90 days (R12) |
| script | enum `ur` / `ur-Latn` | Detected script |
| understood_by | enum `dictionary` / `llm` / `none` | |
| crop_ids, mandi_ids | text[] | Up to 3 pairs (edge case) |
| reply_type | enum | `price`, `price_stale`, `price_other_mandi`, `no_price`, `source_down`, `ask_crop`, `ask_mandi`, `help`, `unsupported`, `list`, `non_text` |
| price_record_ids | bigint[] | Records used in the reply |
| prompt_version | text, nullable | Set when the LLM stage ran |
| model | text, nullable | e.g. `claude-haiku-4-5` |
| replied_at | timestamptz | |
| latency_ms | integer | received → reply sent |
| holding_message_sent | boolean | FR-013 |

## In-memory contracts (not stored)

- **InboundMessage**: `channel`, `contact` (E.164, memory only), `contact_hash`,
  `provider_message_id`, `received_at`, `kind` (`text` / `other`), `text`.
- **OutboundReply**: `channel`, `contact`, `text`, `reply_type`.
- **ExtractionResult**: `crop_ids[]`, `mandi_ids[]`, `intent` (`price` / `list` / `help` /
  `other`), `source` (`dictionary` / `llm`).
