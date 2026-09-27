# Quickstart: Mandi Price Lookup

How to run the feature locally and check that it works. All commands are run from the
repository root.

## Prerequisites

- Python 3.11
- PostgreSQL: Docker (`docker compose up -d db`), or without Docker the `pgserver` package
  (installed with the dev extra) — tests start their own pgserver database automatically
- For live channels only: a Meta WhatsApp Cloud API test number, and SMS aggregator credentials

## 1. Install and configure

```bash
python -m venv .venv
. .venv/Scripts/activate        # Windows Git Bash; use .venv/bin/activate on Linux/macOS
pip install -e ".[dev]"
cp .env.example .env            # then fill in values; never commit .env
docker compose up -d db               # or, without Docker, see "PostgreSQL without Docker" below
alembic upgrade head
python -m kisan.jobs.seed_reference --dev   # reference data + enables the sample price source
```

### PostgreSQL without Docker

The dev extra installs `pgserver`, which bundles PostgreSQL. Start a database that keeps its
data in the git-ignored `.pgdata/` folder and print its URL for `DATABASE_URL` in `.env`:

```bash
python -c "import pgserver; s = pgserver.get_server('.pgdata', cleanup_mode=None); s.psql('CREATE DATABASE kisan;'); print(s.get_uri('kisan'))"
```

(`CREATE DATABASE` fails harmlessly if it already exists.) `alembic`, the jobs, and the app all
read `DATABASE_URL` from `.env`.

Key variables in `.env`:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `CONTACT_HASH_PEPPER` | Secret for hashing phone numbers (research R12) |
| `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Cloud API |
| `SMS_PROVIDER` | `fake` (default) or the chosen vendor |
| `SMS_WEBHOOK_SECRET` | Path secret for `/webhooks/sms/{secret}`, at least 32 characters |
| `ANTHROPIC_API_KEY` | LLM fallback; if unset, only the dictionary stage runs |

## 2. Load prices

```bash
python -m kisan.jobs.fetch_prices --source fixture   # loads recorded fixture prices, no network
# python -m kisan.jobs.fetch_prices --source amis_punjab   # live; only after research R6 VERIFY is done
```

## 3. Run the app

```bash
uvicorn kisan.app:create_app --factory --reload
curl http://localhost:8000/health
```

Expected: `{"status":"ok","database":"ok","newest_price_date":"<a date within 3 days>"}`.

## 4. Try a conversation without WhatsApp or SMS

The fake SMS provider prints replies to the console:

```bash
curl -X POST "http://localhost:8000/webhooks/sms/$SMS_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"from":"+923001234567","message_id":"t1","text":"Multan mandi mein gandum ka rate kya hai?"}'
```

Expected reply (Roman Urdu), for example:
`Multan mandi, Gandum: Rs 3,900–4,050 fi 40 kg. Zariya: AMIS Punjab, 26 Sep.`

Then try:

- Urdu script: `ملتان منڈی میں گندم کا ریٹ کیا ہے؟` → same price, reply in Urdu script.
- Missing mandi: `gandum ka rate?` → bot asks which mandi; reply `Multan` → price.
- Unsupported: `Quetta mandi seb ka rate` → not-supported reply with how to see the list.
- `mandiyan` → list of supported mandis.

## 5. Run the tests

```bash
pytest                              # unit, contract, integration, e2e (Postgres via testcontainers)
pytest tests/eval                   # golden eval set with recorded LLM responses
pytest --cov=kisan --cov-fail-under=80
pip-audit
```

All external services (WhatsApp, SMS, AMIS, Anthropic) are stubbed; the test suite makes no
network calls.
