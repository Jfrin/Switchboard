# Switchboard

An automated inbound lead routing service. It ingests sales inquiries (email or web form), extracts structured data with an LLM, enriches the lead with company info, applies territory and size rules with round-robin assignment, writes the result to HubSpot, and alerts the assigned rep in Slack. Every routing decision is stored in an audit log.

Everything runs in Docker. You do not need Python installed locally.

## Features

- **Ingestion:** `POST /leads` accepts `{from, subject, body}`; processing happens off the request path in a Celery worker
- **LLM extraction:** name, company, role, intent, urgency, country and size pulled into a validated JSON schema, with a regex fallback for email, domain and phone
- **Model fallback:** an ordered list of models (Azure AI Foundry and/or Gemini); a model that runs out of daily quota is skipped until it resets, and the same email is retried on the next one
- **Enrichment:** company size and location from the email domain (cached for 30 days; mock provider included)
- **Routing engine:** intent gate, territory, company-size segment, then round-robin within a team, with rules defined in YAML
- **Human fallback:** spam, "other", and low-confidence leads go to a review queue instead of being guessed at
- **CRM sync:** idempotent create/update of HubSpot contacts and deals (no duplicates on repeat emails)
- **Notifications:** Slack message to the assigned rep with a lead summary
- **Audit log:** every decision is stored with the rule that fired, a confidence score, and the model that answered
- **Evaluation:** labeled datasets with a dev/test split, extraction and routing accuracy, per-model and per-batch-size reports

## Architecture

```
Email / Web form
       |
       v
  FastAPI (ingest) --> Redis queue --> Worker (Celery)
                                          |
                  +-----------------------+------------------------+
                  |                       |                        |
             LLM extraction          Enrichment              Routing engine
        (Azure / Gemini + Pydantic)  (domain lookup)         (YAML rules + RR)
                                                                   |
                                      +----------------------------+
                                      |             |              |
                                  HubSpot        Slack         Postgres
                                  (CRM)        (alerts)      (audit log)
```

## Tech Stack

| Layer | Choice |
|---|---|
| API | Python 3.12, FastAPI |
| Queue / workers | Redis, Celery |
| Validation | Pydantic |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| LLM | Azure AI Foundry (e.g. gpt-4.1-mini) and Google Gemini, with ordered fallback |
| CRM | HubSpot |
| Alerts | Slack incoming webhooks |
| Packaging | Docker, Docker Compose |
| Testing / CI | pytest, ruff, GitHub Actions |

## Getting Started

### Prerequisites

- Docker and Docker Compose
- At least one LLM: an Azure AI Foundry deployment, or a Gemini API key
- A HubSpot service key (optional; use `CRM_MODE=mock` to skip)
- A Slack incoming webhook URL (optional; without it alerts are only logged)

### Setup

```bash
git clone <your-repo-url> switchboard
cd switchboard
cp .env.example .env
# fill in the values in .env
docker compose up -d --build
```

The API is then available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`. Migrations run automatically when the API starts.

### Try it

```bash
# send a sample lead through the whole pipeline and print the result
docker compose exec api python scripts/smoke.py

# list recent leads
docker compose exec api python scripts/smoke.py --list
```

Or with curl:

```bash
curl -X POST http://localhost:8000/leads \
  -H "Content-Type: application/json" \
  -d '{
    "from": "jane.doe@acme.com",
    "subject": "Pricing for 200 seats",
    "body": "Hi, we are a logistics company in Singapore looking for pricing on 200 seats."
  }'
```

The lead is parsed, enriched, assigned to a rep, synced to HubSpot, and announced in Slack. The decision, including `llm_model` (which model answered), appears under `GET /leads/{id}`.

## Configuration

Environment variables (see `.env.example`):

| Variable | Description |
|---|---|
| `LLM_MODELS` | Ordered, comma-separated list. Plain names are Gemini models, `azure:<deployment>` is Azure. Empty means use `GEMINI_MODELS` |
| `GEMINI_MODELS` | Gemini models tried in order (default `gemini-3.5-flash-lite,gemini-3.1-flash-lite`) |
| `GEMINI_API_KEY` | Gemini API key |
| `GEMINI_RPM` | Requests per minute, per Gemini model (default `15`) |
| `GEMINI_BATCH_SIZE` | Eval only: emails per request when Gemini is first in line (default `20`) |
| `AZURE_ENDPOINT` | Resource endpoint ending in `/openai/v1/` |
| `AZURE_API_KEY` | Key for the Azure resource |
| `AZURE_RPM` | Requests per minute, per Azure deployment (default `60`) |
| `DATABASE_URL` | Postgres connection string |
| `REDIS_URL` | Redis connection string |
| `CRM_MODE` | `hubspot` or `mock` |
| `HUBSPOT_TOKEN` | HubSpot service key |
| `HUBSPOT_PORTAL_ID` | Portal id, used for deal links in Slack |
| `HUBSPOT_DEFAULT_OWNER_ID` / `HUBSPOT_OWNER_IDS` | Deal owner ids (`alice=123,bob=456` for per-rep) |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook |
| `ENRICHMENT_PROVIDER` | `mock` (Apollo/Hunter not implemented yet) |
| `CONFIDENCE_THRESHOLD` | Below this, leads go to the review queue (default `0.7`) |

### Choosing models

```dotenv
# Azure first, Gemini as backup
LLM_MODELS=azure:gpt-4.1-mini,gemini-3.5-flash-lite,gemini-3.1-flash-lite

# Gemini only
LLM_MODELS=gemini-3.5-flash-lite,gemini-3.1-flash-lite
```

How failures are handled:

- **Daily-quota 429:** the model is marked exhausted in Redis until the reset time in the error, and every worker skips it
- **503 / 5xx:** short backoff and retry, then the next model (the failing model is skipped for one minute)
- **Per-minute 429:** wait the suggested time and retry
- **All models exhausted:** the lead is retried later by Celery; an eval pauses and keeps its progress

After editing `.env`, recreate the containers:

```bash
docker compose up -d --force-recreate api worker
```

Find HubSpot owner ids with `docker compose exec api python scripts/list_owners.py`.

### Routing rules

Rules live in `config/routing.yaml` and can be changed without touching code:

```yaml
teams:
  smb:
    reps: [alice, bob]
  enterprise:
    reps: [carol, dave]

segments:
  enterprise_min_employees: 500

territories:
  APAC: [SG, PH, AU, JP]
  EMEA: [GB, DE, FR]
  AMER: [US, CA, BR]

fallback_queue: review
```

Assignment order: intent gate (spam and other go to review), confidence check, territory, segment, then round-robin within the matching team.

## Commands

All commands run through Docker from the project folder. Use `exec` for things that talk to the running API, and `run --rm` for one-off jobs.

### Run and inspect

```bash
docker compose up -d --build                      # start everything
docker compose up -d --build --force-recreate api worker   # after changing .env or code
docker compose ps                                 # what is running
docker compose logs api --tail 50                 # API log
docker compose logs worker --tail 50              # worker log (LLM and HubSpot calls)
docker compose down                               # stop (add -v to wipe the database)
docker compose exec api alembic upgrade head      # run migrations by hand
docker compose exec api alembic current           # show migration version
```

### Test and lint

```bash
docker compose run --rm api python -m pytest -q
docker compose run --rm api ruff check app tests eval scripts
```

### Build the datasets

All eval files live in `eval/`.

| File | What it is |
|---|---|
| `dataset.jsonl` | 138 clean synthetic emails (regenerate with `scripts/make_dataset.py`) |
| `messy.jsonl` | 38 hand-written hard cases; cannot be regenerated, keep it |
| `synthetic_dataset.jsonl` | the large raw synthetic set you supply |
| `synthetic_dev.jsonl` / `synthetic_test.jsonl` | generated dev and held-out test split |

```bash
# regenerate the clean 138-row set
docker compose run --rm api python scripts/make_dataset.py

# split the large raw set into a deduped, seeded dev/test pair
docker compose run --rm api python scripts/prep_synthetic.py --n 1000

# options: total rows, seed, test share, per-company cap, input file
docker compose run --rm api python scripts/prep_synthetic.py --n 200 --seed 3 --test-frac 0.3 --max-per-company 5
docker compose run --rm api python scripts/prep_synthetic.py --input eval/my_file.jsonl
```

`prep_synthetic.py` drops empty and duplicate emails, caps how often one company appears, samples stratified by expected team, and writes `synthetic_dev.jsonl` and `synthetic_test.jsonl` with the same team mix. Tune on dev only; run test once at the end.

### Run the evaluation

```bash
# default: uses LLM_MODELS from .env
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl

# the clean and hand-written sets
docker compose run --rm api python eval/run_eval.py
docker compose run --rm api python eval/run_eval.py --file messy.jsonl

# quick check on the first N rows
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl --limit 30
```

**Pick the model for one run** with `--model` (comma-separated, tried in order, overrides `LLM_MODELS`):

```bash
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl --model azure:gpt-4.1-mini
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl --model gemini-3.5-flash-lite
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl --model gemini-3.1-flash-lite
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl --model azure:gpt-4.1-mini,gemini-3.5-flash-lite
```

**Batching** (several emails per request) exists because Gemini's free tier limits requests per day, not tokens. It is automatic by default: `GEMINI_BATCH_SIZE` (20) when Gemini is the model answering, 1 for Azure. If Azure fails mid-run and Gemini takes over, later requests start batching by themselves. Force a size with `--batch`:

```bash
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl --model gemini-3.5-flash-lite --batch 20
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl --model gemini-3.5-flash-lite --batch 50
docker compose run --rm api python eval/run_eval.py --file synthetic_dev.jsonl --model gemini-3.5-flash-lite --batch 1   # no batching
```

Larger batches use fewer requests but can lower accuracy. Compare sizes on the same rows (`--limit 100`) and keep the largest one whose numbers match `--batch 1`. Emails the model skips or garbles in a batch are re-done on their own.

**Resume:** extraction answers are cached in `eval/.cache/` per dataset, model list and batch size. If a run crashes or every model runs out of quota it exits with a pause message; run the same command again to continue. Delete `eval/.cache/` to force a fresh run.

**Results:** written to `eval/results*.md`. Runs that use `--model` or `--batch` add the model and batch size to the file name, so different runs do not overwrite each other. Each file reports extraction accuracy per field, routing accuracy (also without the two mock-enrichment domains, whose labels conflict with the mock table), a confusion matrix, the miss lists, and how many emails each model answered.

Reporting rules: tune on dev only, report the held-out test number with the model that produced it, and call everything synthetic or hand-written unless real data is added.

## Project Structure

```
switchboard/
├── app/
│   ├── api/            # FastAPI routes
│   ├── workers/        # Celery tasks
│   ├── extraction/     # LLM calls, fallback, batching, rate limits, schema
│   ├── enrichment/     # Provider clients and cache
│   ├── routing/        # Rule engine and round-robin
│   ├── integrations/   # HubSpot and Slack clients
│   ├── db/             # Models
│   └── main.py
├── config/
│   └── routing.yaml
├── eval/               # datasets, run_eval.py, results, .cache/
├── migrations/         # Alembic
├── scripts/            # smoke.py, list_owners.py, prep_synthetic.py, make_dataset.py
├── tests/
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── README.md
```

## Design Notes

- **Idempotency:** contacts are matched on email before creating anything in HubSpot, so repeat inquiries update rather than duplicate.
- **Validation:** LLM output must pass the Pydantic schema; failures are retried once, then the regex fallback fills what it can and the lead goes to review.
- **Spam and prompt injection:** the model only extracts fields; routing is decided by code. Spam and "other" intents never reach a rep, whatever the email says.
- **Round-robin state** is kept in Postgres with a row lock, so it survives restarts and works across multiple workers.
- **Quota handling:** per-model rate limiters and exhaustion marks live in Redis, shared by every worker.

## License

MIT
