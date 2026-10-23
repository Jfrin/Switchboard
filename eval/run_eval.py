"""Evaluate extraction and routing against eval/dataset.jsonl.

Usage: python eval/run_eval.py [--limit N]
Writes eval/results.md. Requires GEMINI_API_KEY for real LLM extraction (throttled to GEMINI_RPM).
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.config import get_settings
from app.enrichment import enrich
from app.extraction.extractor import extract_lead
from app.routing.engine import load_rules, route

ROOT = Path(__file__).parent
FIELDS = ["company", "intent", "country"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    settings = get_settings()
    rules = load_rules(settings.routing_config_path)
    rows = [json.loads(line) for line in (ROOT / "dataset.jsonl").read_text().splitlines() if line]
    rows = rows[: args.limit]

    field_hits: dict[str, int] = defaultdict(int)
    confusion: Counter[tuple[str, str]] = Counter()
    team_hits = 0

    for row in rows:
        lead = extract_lead(row["from"], row["subject"], row["body"])
        info = enrich(lead.domain)
        decision = route(
            country=lead.country or info.get("country"),
            employee_count=lead.employee_count or info.get("employee_count"),
            confidence=lead.confidence,
            rules=rules,
            threshold=settings.confidence_threshold,
            pick_rep=lambda team, reps: reps[0],
        )
        exp = row["expected"]
        for f in FIELDS:
            field_hits[f] += getattr(lead, f) == exp[f]
        confusion[(exp["team"], decision.team)] += 1
        team_hits += decision.team == exp["team"]

    n = len(rows)
    lines = ["# Evaluation results", "", f"Samples: {n}", "", "## Extraction accuracy", ""]
    lines += [f"- {f}: {field_hits[f] / n:.0%}" for f in FIELDS]
    lines += ["", f"## Routing accuracy: {team_hits / n:.0%}", ""]
    lines += ["## Confusion (expected -> got)", ""]
    lines += [f"- {e} -> {g}: {c}" for (e, g), c in sorted(confusion.items())]
    out = "\n".join(lines) + "\n"
    (ROOT / "results.md").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
