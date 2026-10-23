# Switchboard

An automated inbound lead routing service. It ingests sales inquiries (email or web form), extracts structured data with an LLM, enriches the lead with company info, applies territory and size rules with round-robin assignment, writes the result to HubSpot, and alerts the assigned rep in Slack. Every routing decision is stored in an audit log.

## Features

- **Ingestion:** inbound email (Gmail API / IMAP) or a webhook endpoint for web forms
- **LLM extraction:** name, company, role, intent, urgency, and region pulled into a validated JSON schema
- **Enrichment:** company size and location from the email domain (Apollo/Hunter/Clearbit, with a mock fallback)
- **Routing engine:** territory, company-size segment, and round-robin within a team, with rules defined in YAML
- **Human fallback:** low-confidence leads go to a review queue instead of being guessed at
- **CRM sync:** idempotent create/update of HubSpot contacts and deals (no duplicates on repeat emails)
- **Notifications:** Slack message to the assigned rep with a lead summary
- **Audit log:** every decision is stored with the rule that fired and a confidence score
- **Evaluation:** labeled test set with extraction and routing accuracy reports

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
             (Pydantic schema)       (domain lookup)         (YAML rules + RR)
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
| LLM | Claude API |
| CRM | HubSpot (free developer account) |
| Alerts | Slack incoming webhooks |
| Packaging | Docker, Docker Compose |
| Testing / CI | pytest, GitHub Actions |

## Getting Started

### Prerequisites

- Docker and Docker Compose
- An Anthropic API key
- A HubSpot developer account with a private app token (optional; use `CRM_MODE=mock` to skip)
- A Slack incoming webhook URL (optional)

### Setup

```bash
git clone <your-repo-url> lead-router
cd lead-router
cp .env.example .env
# fill in the values in .env
docker compose up --build
```

The API is then available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

### Try it

```bash
curl -X POST http://localhost:8000/leads \
  -H "Content-Type: application/json" \
  -d '{
    "from": "jane.doe@acme.com",
    "subject": "Pricing for 200 seats",
    "body": "Hi, we are a logistics company in Singapore looking for pricing on 200 seats."
  }'
```

Expected result: the lead is parsed, enriched, assigned to a rep, synced to HubSpot, and announced in Slack. The decision appears under `GET /leads/{id}`.

## Configuration

Environment variables (see `.env.example`):

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Key for LLM extraction |
| `DATABASE_URL` | Postgres connection string |
| `REDIS_URL` | Redis connection string |
| `HUBSPOT_TOKEN` | HubSpot private app token |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook |
| `ENRICHMENT_PROVIDER` | `apollo`, `hunter`, or `mock` |
| `CRM_MODE` | `hubspot` or `mock` |
| `CONFIDENCE_THRESHOLD` | Below this, leads go to the review queue (default `0.7`) |

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

Assignment order: territory, then segment, then round-robin within the matching team.

## Project Structure

```
lead-router/
├── app/
│   ├── api/            # FastAPI routes
│   ├── workers/        # Celery tasks
│   ├── extraction/     # LLM prompts and Pydantic schemas
│   ├── enrichment/     # Provider clients
│   ├── routing/        # Rule engine and round-robin
│   ├── integrations/   # HubSpot and Slack clients
│   ├── db/             # Models and migrations
│   └── main.py
├── config/
│   └── routing.yaml
├── eval/
│   ├── dataset.jsonl   # Labeled sample inquiries
│   └── run_eval.py
├── tests/
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── README.md
```

## Testing and Evaluation

```bash
# unit and integration tests
docker compose run --rm api pytest

# routing/extraction accuracy on the labeled set
docker compose run --rm api python eval/run_eval.py
```

The evaluation script reports field-level extraction accuracy, routing accuracy, and a confusion matrix for team assignment.

## Design Notes

- **Idempotency:** contacts are matched on email and domain before creating anything in HubSpot, so repeat inquiries update rather than duplicate.
- **Validation:** LLM output must pass the Pydantic schema; failures are retried once, then sent to the review queue.
- **Privacy:** raw email bodies are stored only in the audit log and can be purged on a retention schedule.
- **Round-robin state** is kept in Postgres, so it survives restarts and works across multiple workers.

## License

MIT
