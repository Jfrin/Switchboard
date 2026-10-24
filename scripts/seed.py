"""Load a set of sample leads for a one-command demo. Runs inside the api container.

    docker compose exec api python scripts/seed.py
    docker compose exec api python scripts/seed.py --file eval/dataset.jsonl --limit 20

Posts each lead to the API, waits for the worker, and prints a table of who got what.
With CRM_MODE=hubspot every routed lead creates a real contact and deal, so the script
refuses to run in that mode unless you pass --allow-hubspot.
"""

import argparse
import json
import sys
import time

import httpx

from app.config import get_settings

API = "http://localhost:8000"

SAMPLES = [
    (
        "jane.doe@acme.com",
        "Pricing for 200 seats",
        "Hi, we are a logistics company in Singapore with about 220 employees. "
        "Looking for pricing.",
    ),
    (
        "cto@northwind-energy.com",
        "Enterprise demo request",
        "Northwind Energy, Houston, USA. We have 4,200 employees and want a demo.",
    ),
    (
        "procurement@bavaria-motors.de",
        "Partnership enquiry",
        "Bavaria Motors in Munich, Germany (about 1,800 staff). Interested in reselling.",
    ),
    (
        "hello@lumen-studio.co.uk",
        "Quick demo?",
        "Lumen Studio, London UK, 35 people. Could we get a demo this week? Urgent.",
    ),
    (
        "kenji.s@gmail.com",
        "Support question",
        "I work at Sakura Robotics in Osaka, around 140 employees. Our login stopped working.",
    ),
    (
        "maria@tropicana-foods.com.br",
        "Pricing",
        "Tropicana Foods, Sao Paulo Brazil, roughly 900 employees. Send enterprise pricing.",
    ),
    (
        "ravi@delhi-textiles.in",
        "Demo request",
        "Delhi Textiles, India, 300 employees, would like a demo.",
    ),
    ("someone@outlook.com", "hi", "Need more info about your product."),
    (
        "seo_team@rankings-fast-marketing.com",
        "Rank #1 on Google in 7 days!!!",
        "We guarantee first page rankings. Reply now for our special SEO package.",
    ),
    (
        "applicant_7@gmail.com",
        "Application for Senior Engineer",
        "I am writing to apply for the Senior Engineer role. Resume attached.",
    ),
    (
        "jane.doe@acme.com",
        "Re: Pricing for 200 seats",
        "Following up on my earlier note about pricing for 200 seats.",
    ),
    ("xq9z_77@anonmail.net", "", "qwertyuiop1234567890_zxCVBNM!!!"),
]


def wait_for_api() -> None:
    for _ in range(30):
        try:
            httpx.get(f"{API}/health").raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(1)
    sys.exit("API did not come up within 30s; check: docker compose logs api")


def load(file: str | None, limit: int | None) -> list[dict]:
    if not file:
        return [{"from": f, "subject": s, "body": b} for f, s, b in SAMPLES]
    with open(file, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    return [{k: r[k] for k in ("from", "subject", "body")} for r in rows[:limit]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="JSONL of {from, subject, body, ...} instead of the built-ins")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=300, help="seconds to wait for the worker")
    ap.add_argument("--allow-hubspot", action="store_true")
    args = ap.parse_args()

    crm = get_settings().crm_mode
    if crm == "hubspot" and not args.allow_hubspot:
        sys.exit(
            "CRM_MODE=hubspot: this would create real contacts and deals in HubSpot.\n"
            "Set CRM_MODE=mock in .env (then recreate api and worker), or pass --allow-hubspot."
        )

    wait_for_api()
    leads = load(args.file, args.limit)
    ids = []
    for payload in leads:
        res = httpx.post(f"{API}/leads", json=payload)
        res.raise_for_status()
        ids.append(res.json()["id"])
    print(f"posted {len(ids)} leads (CRM_MODE={crm}); waiting for the worker...")

    results: dict[str, dict] = {}
    deadline = time.time() + args.timeout
    while time.time() < deadline and len(results) < len(ids):
        for lead_id in ids:
            if lead_id in results:
                continue
            lead = httpx.get(f"{API}/leads/{lead_id}").json()
            if lead["status"] not in ("queued", "processing"):
                results[lead_id] = lead
        time.sleep(2)

    print(f"\n{'sender':38} {'status':9} {'assigned':22} {'rule':42} model")
    by_dest: dict[str, int] = {}
    for lead_id, payload in zip(ids, leads, strict=True):
        lead = results.get(lead_id)
        if lead is None:
            print(f"{payload['from'][:38]:38} (still processing)")
            continue
        d = lead.get("decision") or {}
        dest = d.get("rep") or d.get("team") or "-"
        by_dest[dest] = by_dest.get(dest, 0) + 1
        print(
            f"{payload['from'][:38]:38} {lead['status']:9} {dest[:22]:22} "
            f"{(d.get('rule') or lead.get('error') or '-')[:42]:42} {lead.get('llm_model') or '-'}"
        )
    print("\nassigned to:", ", ".join(f"{k}={v}" for k, v in sorted(by_dest.items())))
    if len(results) < len(ids):
        print(f"{len(ids) - len(results)} lead(s) not finished; check: docker compose logs worker")


if __name__ == "__main__":
    main()
