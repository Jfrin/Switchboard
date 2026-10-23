"""Evaluate extraction and routing against eval/dataset.jsonl.

Usage: python eval/run_eval.py [--limit N]
Writes eval/results.md. Needs GEMINI_API_KEY; calls are throttled to GEMINI_RPM,
so a full run takes roughly (rows / GEMINI_RPM) minutes.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.config import get_settings
from app.enrichment import enrich
from app.extraction.extractor import LLMUnavailable, extract_lead
from app.routing.engine import load_rules, route

ROOT = Path(__file__).parent
FIELDS = ["company", "intent", "country"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    settings = get_settings()
    rules = load_rules(settings.routing_config_path)
    path = ROOT / "dataset.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    rows = rows[: args.limit]

    field_hits: dict[str, int] = defaultdict(int)
    confusion: Counter[tuple[str, str]] = Counter()
    team_hits = 0
    errors = 0
    misses: list[str] = []

    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['from']}", flush=True)
        try:
            lead = extract_lead(row["from"], row["subject"], row["body"])
        except LLMUnavailable as exc:
            errors += 1
            print(f"  skipped: {exc}", flush=True)
            continue
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
        if decision.team == exp["team"]:
            team_hits += 1
        else:
            misses.append(
                f"- {row['from']}: expected {exp['team']}, got {decision.team} "
                f"({decision.rule}; country={lead.country}, "
                f"employees={lead.employee_count}, confidence={lead.confidence})"
            )

    n = len(rows) - errors
    if n == 0:
        print("no rows evaluated")
        return
    lines = ["# Evaluation results", "", f"Samples evaluated: {n} (skipped on LLM error: {errors})"]
    lines += ["", "## Extraction accuracy", ""]
    lines += [f"- {f}: {field_hits[f] / n:.1%}" for f in FIELDS]
    lines += ["", f"## Routing accuracy: {team_hits / n:.1%}", ""]
    lines += ["## Confusion (expected -> got)", ""]
    lines += [f"- {e} -> {g}: {c}" for (e, g), c in sorted(confusion.items())]
    if misses:
        lines += ["", "## Routing misses", ""] + misses
    out = "\n".join(lines) + "\n"
    (ROOT / "results.md").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
