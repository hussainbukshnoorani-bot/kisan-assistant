# Feature Specification: Mandi Price Lookup

**Feature Branch**: `002-mandi-price-lookup`  
**Created**: 2026-09-26  
**Status**: Draft  
**Input**: User description: "Farmer asks the price of a crop at a named mandi in Urdu or Roman Urdu and gets the latest price with its source and date"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask a crop price at a named mandi (Priority: P1)

A farmer sends a message such as "Multan mandi mein gandum ka rate kya hai?" or
"ملتان منڈی میں گندم کا ریٹ کیا ہے؟". The bot replies in the same script with the latest
available price for that crop at that mandi, in the unit farmers use (Rs per 40 kg), stating
where the price came from and the date it applies to.

**Why this priority**: Knowing today's rate before travelling to a mandi or selling to a
middleman is the most frequent, highest-value question farmers ask, and it is the core of the
product.

**Independent Test**: Send a price question for a supported crop and mandi in Roman Urdu and
again in Urdu script; verify each reply is in the matching script, contains the correct price
from the reference data, the unit, the source name, and the price date.

**Acceptance Scenarios**:

1. **Given** today's wheat price for Multan mandi is available, **When** a farmer asks
   "Multan mandi mein gandum ka rate kya hai?", **Then** the bot replies in Roman Urdu with
   the price per 40 kg, the source name, and today's date.
2. **Given** the same data, **When** a farmer asks the same question in Urdu script, **Then**
   the reply is in Urdu script with the same price, source, and date.
3. **Given** the price data includes a minimum and maximum rate for the day, **When** a farmer
   asks for that crop and mandi, **Then** the reply shows the range (min–max) rather than a
   single invented figure.
4. **Given** a farmer uses a spelling variant ("gehun", "gandum", "wheat", "گندم") or a variant
   mandi name ("Multan", "ملتان"), **When** they ask for the price, **Then** the bot recognises
   the crop and mandi and answers correctly.

---

### User Story 2 - Honest answers when data is missing or old (Priority: P2)

When the bot has no price for the requested crop and mandi, or the latest price is older than
the allowed freshness limit, it says so clearly instead of guessing, and where possible offers
the most recent price available with its date or the price at a neighbouring supported mandi.

**Why this priority**: A wrong or outdated price can cost a farmer money on a sale. Being
honest about gaps is what makes the P1 answers trustworthy.

**Independent Test**: Remove today's data for one mandi and set another mandi's last price to
older than the freshness limit; verify the bot never presents either as current and always
states the actual date.

**Acceptance Scenarios**:

1. **Given** no price exists for the requested crop at the requested mandi, **When** the farmer
   asks, **Then** the bot says the price is not available and does not state any figure for
   that mandi.
2. **Given** the latest price is older than the freshness limit, **When** the farmer asks,
   **Then** the bot either withholds it or clearly labels it with its date as not current.
3. **Given** no current price for the requested mandi but a current price exists at one of its
   listed neighbouring mandis, **When** the farmer asks, **Then** the bot may offer that price,
   clearly naming the other mandi.
4. **Given** the bot cannot read its price data (its database is unavailable) or cannot finish
   the answer within 9 seconds, **When** the farmer asks, **Then** the bot replies within the
   normal time limit that prices cannot be fetched right now and suggests asking again later.
   (A failed price collection run does not trigger this reply; it only makes prices stale or
   missing, which scenarios 1 and 2 cover.)

---

### User Story 3 - Clarify incomplete or ambiguous questions (Priority: P3)

When a farmer's message is missing the crop or the mandi, or names something ambiguous, the bot
asks one short question in the farmer's script and then answers once the farmer replies.

**Why this priority**: Many real messages are short ("gandum ka rate?"); resolving them with a
single follow-up keeps the conversation usable without guessing.

**Independent Test**: Send a message with only a crop, then reply with a mandi name; verify the
bot asks exactly one clarifying question and then returns the correct price.

**Acceptance Scenarios**:

1. **Given** a message naming a crop but no mandi, **When** the farmer sends it, **Then** the bot
   asks which mandi, and on the farmer's reply returns that mandi's price.
2. **Given** a message naming a mandi but no crop, **When** the farmer sends it, **Then** the bot
   asks which crop, and on the reply returns the price.
3. **Given** a message the bot cannot relate to crop prices (e.g. a greeting or an off-topic
   question), **When** the farmer sends it, **Then** the bot briefly explains what it can help
   with and gives one example question in the farmer's script.

---

### Edge Cases

- A farmer asks for several crops or mandis in one message: on WhatsApp the bot answers up to 3
  crop–mandi pairs in one reply; on SMS it answers as many pairs as fit in the FR-001a budget
  (at least 1). In both cases it asks the farmer to send the rest separately.
- A farmer mixes Urdu script and Roman Urdu in one message: the bot replies in the script used
  for the majority of the message.
- A farmer who used SMS switches to WhatsApp (or the reverse): each channel is handled on its
  own; a pending clarification on one channel does not carry over to the other.
- A farmer names a crop or mandi the bot does not cover: the bot says it is not yet supported
  and lists how to find supported ones (e.g. "send 'mandiyan' for the list").
- The source reports a price in a unit other than per 40 kg: the bot converts it and still
  states the unit clearly.
- Price data contains an obviously invalid value (zero, negative, or far outside the recent
  range): the value is not shown to farmers and the issue is recorded for review.
- A message tries to make the bot change its instructions or invent a price: the bot answers
  only from available data.
- The farmer sends a voice note, image, or sticker: the bot replies that it can only read text
  messages for now.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept text messages from farmers through both WhatsApp and SMS, and
  MUST reply on the same channel the farmer used. Price answers MUST be identical in content
  across channels; only length and formatting may differ.
- **FR-001a**: On SMS, a price reply MUST fit in at most 2 SMS segments (the character budget is
  lower for Urdu script than for Roman Urdu), dropping optional text before any required field
  from FR-005. Roman Urdu SMS replies MUST use only GSM-7 characters (e.g. a plain hyphen, not an
  en dash) so they are not forced into the smaller Unicode budget.
- **FR-002**: System MUST understand price questions written in Urdu script, Roman Urdu, and
  mixed text, including common spelling variants of supported crop and mandi names.
- **FR-003**: System MUST reply in the script the farmer used (Urdu script or Roman Urdu).
- **FR-004**: System MUST answer with prices only from retrieved price data; it MUST NOT
  estimate, predict, or generate a price.
- **FR-005**: Every price reply MUST include the crop, the mandi, the price (or min–max range),
  the unit (Rs per 40 kg by default), the source name, and the date the price applies to.
- **FR-006**: System MUST treat a price as current only if it is no older than 3 days; older
  prices MUST be labelled with their date as not current, or withheld.
- **FR-007**: System MUST state clearly when no price is available and MUST NOT show a figure
  for that crop–mandi pair.
- **FR-008**: System MAY offer a current price from one of the requested mandi's listed
  neighbouring mandis (a reviewed list kept with the mandi reference data) when the requested
  one has no current price, and MUST name that mandi explicitly.
- **FR-009**: System MUST ask exactly one short clarifying question when the crop or mandi is
  missing or ambiguous, and MUST remember the partial question for the farmer's next message
  for at least 30 minutes.
- **FR-010**: System MUST cover, at launch, 5 crops (wheat, cotton (phutti), Basmati paddy,
  IRRI paddy, maize) at 10 main Punjab mandis (Lahore, Multan, Faisalabad, Gujranwala,
  Rawalpindi, Sahiwal, Bahawalpur, Sargodha, Okara, Rahim Yar Khan). A general rice word
  ("chawal", "dhaan", "munji", "چاول", "دھان") MUST return both paddy varieties; a variety word
  ("basmati", "IRRI") returns that variety only. Asking about sugarcane gets the "not yet
  supported" reply. *(Default adopted 2026-09-26 because Q2 was not answered. Sugarcane dropped
  and paddy split into two crops on 2026-09-26 after the AMIS check — research R6
  verification; the paddy split was the user's decision.)*
- **FR-011**: System MUST provide a list of supported crops and mandis when a farmer asks for it.
- **FR-012**: WhatsApp replies MUST be no longer than 480 characters (SMS replies follow
  FR-001a), and all replies MUST be understandable
  without images or links.
- **FR-013**: System MUST reply within 10 seconds; if a price lookup takes longer than 5 seconds,
  it MUST send a short "checking" message first.
- **FR-014**: System MUST NOT ask farmers for any personal information (CNIC, bank details,
  land details) to answer a price question.
- **FR-015**: System MUST reject invalid price values (zero, negative, or outside a plausible
  range for that crop) and record them for review rather than show them.
- **FR-016**: System MUST record, for each reply, which price record and source it used and when
  that record was fetched, so any answer can be traced later.
- **FR-017**: System MUST only use price sources that are publicly available and whose terms
  allow this use.
- **FR-018**: If a farmer's message contains a CNIC number or a phone number, the system MUST
  replace it with a placeholder before the text is stored, logged, or sent to any AI model.
- **FR-019**: If a messaging provider delivers the same message more than once, the system MUST
  reply only once.

### Key Entities

- **Farmer**: A person messaging the bot, identified only by their messaging contact. Attributes:
  channel (WhatsApp or SMS), preferred script (inferred from their last message), pending
  clarification (if any).
- **Crop**: A supported commodity (e.g. wheat, cotton, rice, sugarcane, maize) with its names in
  Urdu, Roman Urdu, and English, including spelling variants, and a plausible price range.
- **Mandi**: A supported market with its names in Urdu, Roman Urdu, and English, its district,
  and its province.
- **Price Record**: A price for one crop at one mandi on one date. Attributes: min price, max
  price (or single price), unit, source, price date, time fetched, validity status.
- **Price Source**: A publicly available provider of mandi prices. Attributes: name, terms-of-use
  note, coverage, update frequency.
- **Conversation Turn**: One farmer message and the bot's reply, linked to the price records
  used, for traceability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A farmer asking a clear question about a supported crop and mandi receives the
  correct price in one reply, with no follow-up, in at least 90% of test questions.
- **SC-002**: At least 90% of a test set of real-style questions written by native speakers
  (half Urdu script, half Roman Urdu) are understood correctly on the first attempt.
- **SC-003**: 100% of price replies include source and date; 0 replies present a price that is
  missing, older than 3 days, or invalid as current.
- **SC-004**: 95% of replies arrive within 10 seconds, and half arrive within 5 seconds, on
  both WhatsApp and SMS (excluding carrier delivery delays outside the system's control).
- **SC-005**: In a pilot with at least 20 farmers, at least 80% say the answer was clear and
  useful, and at least 60% ask a second price question within two weeks.
- **SC-006**: Incomplete questions are resolved to a correct price within two bot messages in at
  least 85% of cases.

## Assumptions

- Farmers message from their own phones; no sign-up or account is required for price lookups.
- Default unit is rupees per 40 kg (one maund), since that is how mandi rates are usually
  quoted; other units are converted.
- A price is "current" for up to 3 days, to allow for weekends, holidays, and sources that do
  not update daily.
- Publicly available daily mandi price data exists for the launch crops and mandis (for example,
  from provincial agriculture or market committee publications); the exact sources are chosen
  and checked for terms of use during planning.
- Farmers on basic phones use SMS; farmers with smartphones mostly use WhatsApp. The same
  phone number on both channels is treated as two separate conversations in this feature.
- WhatsApp replies outside the 24-hour customer-service window are not needed, because every
  reply in this feature answers a message the farmer just sent.
- Voice notes are out of scope for this feature; text only.
- Weather advice and financing eligibility are separate features and out of scope here.
