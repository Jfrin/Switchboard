First stable release of Switchboard: an inbound lead routing service. It takes sales inquiries (email or web form), extracts structured data with an LLM, enriches the lead, routes it by territory and company size with round-robin assignment, creates the contact and deal in HubSpot, alerts the rep in Slack, and records every decision in an audit log. Everything runs in Docker.

## Highlights
- **Pipeline:** FastAPI ingest, Redis queue, Celery worker, Postgres
- **LLM extraction** with Pydantic validation, one retry, and a regex fallback
- **Model fallback:** an ordered list of Azure AI Foundry and Gemini models, with per-model rate limits, daily-quota tracking shared across workers, and failover on outages and content-filter refusals
- **Routing engine:** intent gate, confidence threshold, territory, segment, then round-robin, with rules in `config/routing.yaml`
- **Review queue** for spam, low-confidence, no-territory and content-filtered leads, with the rule recorded in the audit log
- **HubSpot** contact and deal creation (idempotent), deal owner set to the assigned rep
- **Slack** alerts with a lead summary and deal link
- **Evaluation harness:** dev and test splits, per-model and per-batch-size reports, resumable runs
- **Seed script** for a one-command demo: `docker compose exec api python scripts/seed.py`

## Evaluation (synthetic data)
On 120 synthetic emails with `azure:gpt-4.1-mini`: routing accuracy 97.5% (99.2% excluding two rows whose labels conflict with the mock enrichment table) and intent accuracy 100%. These are synthetic and hand-written datasets, not real customer email. Details are in `eval/results*.md`.

## Known limitations
- Enrichment uses a mock provider; Apollo and Hunter are not implemented yet
- Failed leads are marked `failed` with the error; there is no separate dead-letter queue
- Repeat senders are not pinned to their first rep
- No metrics dashboard yet

## Quick start
```
cp .env.example .env
docker compose up -d --build
docker compose exec api python scripts/seed.py
```
