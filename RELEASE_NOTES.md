Switchboard now routes more than sales leads. A **profile** file decides what the AI reads and how items are routed, and a small web page edits profiles. This release also adds observability.

## What's new
- **Profiles:** one YAML file defines categories, extracted fields, derived fields, teams and ordered routing rules. One profile is active at a time (`PROFILE_PATH` in `.env`). HubSpot and Slack are per-profile on/off switches.
- **Two profiles included:** `sales` (the previous behavior, now the default) and `support` (ticket triage: outage, bug, billing, and so on, routed by category, severity and plan).
- **Profile editor at `/admin`** (off by default, `ADMIN_UI=true`): YAML editor with live validation, a rule summary, save, copy, and a form tab for common edits, **Make active** to switch profiles without touching `.env`, and a tester that shows what the AI extracts and where a message would route. Edits apply to the next message without a restart.
- **Sticky reps:** a repeat sender goes to the rep they were last routed to (per-profile switch `sticky_reps`).
- **Failed leads can be retried:** `POST /leads/{id}/retry` and `POST /leads/retry-failed` put them back on the queue.
- **Observability:** JSON logs, a `/metrics` endpoint, and a provisioned Grafana dashboard (optional compose profile `observability`).
- **Eval:** `run_eval.py --profile` scores any profile; a 20-row hand-written set for the support profile is included.
- **Env overrides:** `ROUTING_*` still override the profile; new `ROUTING_TEAM_<NAME>_REPS` works for any team.

## Upgrading from v1.0.0
- `config/routing.yaml` is replaced by `config/profiles/sales.yaml`. In `.env`, remove `ROUTING_CONFIG_PATH` and add `PROFILE_PATH=config/profiles/sales.yaml`.
- A low-confidence spam email is now labelled `fallback:low_confidence` instead of `fallback:intent_spam`. It still goes to review.
- The sales profile no longer extracts a separate `region` field; `region` is now computed from `country`.
- Rebuild: `docker compose up -d --build --force-recreate api worker`

## Known limitations
- The support profile has only been checked with a stub model, not scored against a real one
- Enrichment uses a mock provider; Apollo and Hunter are not implemented
- Failed leads are retried by hand through the API; there is no automatic dead-letter handling beyond the worker's own retries
- The profile editor has no login beyond the optional `ADMIN_TOKEN`, so keep it off or protected on shared networks
