"""Evaluate extraction and routing against eval/dataset.jsonl.

Usage: python eval/run_eval.py [--limit N]
Writes eval/results.md. Needs GEMINI_API_KEY; calls are throttled to GEMINI_RPM,
so a full run takes roughly (rows / GEMINI_RPM) minutes.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from app.config import get_settings
from app.enrichment import enrich
from app.extraction.extractor import LLMUnavailable, extract_lead_with_model
from app.extraction.schema import Lead
from app.routing.engine import load_rules, route

ROOT = Path(__file__).parent
FIELDS = ["company", "intent", "country"]


def row_key(row: dict) -> str:
    return hashlib.sha1(f"{row['from']}\n{row['subject']}\n{row['body']}".encode()).hexdigest()


def load_cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {
        r["key"]: r for r in (json.loads(x) for x in path.read_text("utf-8").splitlines() if x)
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--file", default="dataset.jsonl", help="dataset inside eval/")
    args = ap.parse_args()

    settings = get_settings()
    rules = load_rules(settings.routing_config_path)
    path = ROOT / args.file
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    rows = rows[: args.limit]
    results_name = "results.md" if args.file == "dataset.jsonl" else f"results-{path.stem}.md"

    # Extraction results are saved per row, so a crash or an exhausted quota loses nothing:
    # run the same command again and finished rows are read from the cache.
    cache_path = ROOT / ".cache" / f"{path.stem}.jsonl"
    cache_path.parent.mkdir(exist_ok=True)
    cache = load_cache(cache_path)
    models: Counter[str] = Counter()

    field_hits: dict[str, int] = defaultdict(int)
    confusion: Counter[tuple[str, str]] = Counter()
    team_hits = 0
    misses: list[str] = []
    field_misses: list[str] = []

    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['from']}", flush=True)
        key = row_key(row)
        if key in cache:
            lead, model = Lead(**cache[key]["lead"]), cache[key].get("model")
        else:
            try:
                lead, model = extract_lead_with_model(row["from"], row["subject"], row["body"])
            except LLMUnavailable as exc:
                hours = exc.retry_after / 3600
                print(
                    f"\nPaused at row {i}: {exc}\nProgress is saved ({len(cache)} rows). "
                    f"Re-run the same command in about {hours:.1f}h to resume.",
                    flush=True,
                )
                sys.exit(2)
            with cache_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "model": model, "lead": lead.model_dump()}) + "\n")
            cache[key] = {"key": key, "model": model, "lead": lead.model_dump()}
        models[model or "none (regex fallback)"] += 1
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
            got = getattr(lead, f)
            field_hits[f] += got == exp[f]
            if got != exp[f]:
                field_misses.append(f"- {row['from']}: {f} expected {exp[f]!r}, got {got!r}")
        confusion[(exp["team"], decision.team)] += 1
        if decision.team == exp["team"]:
            team_hits += 1
        else:
            misses.append(
                f"- {row['from']}: expected {exp['team']}, got {decision.team} "
                f"({decision.rule}; country={lead.country}, "
                f"employees={lead.employee_count}, confidence={lead.confidence})"
            )

    n = len(rows)
    if n == 0:
        print("no rows evaluated")
        return
    lines = ["# Evaluation results", "", f"Samples evaluated: {n}"]
    lines += ["", "Answered by: " + ", ".join(f"{m} ({c})" for m, c in models.most_common())]
    lines += ["", "## Extraction accuracy", ""]
    lines += [f"- {f}: {field_hits[f] / n:.1%}" for f in FIELDS]
    lines += ["", f"## Routing accuracy: {team_hits / n:.1%}", ""]
    lines += ["## Confusion (expected -> got)", ""]
    lines += [f"- {e} -> {g}: {c}" for (e, g), c in sorted(confusion.items())]
    if field_misses:
        lines += ["", "## Extraction misses", ""] + field_misses
    if misses:
        lines += ["", "## Routing misses", ""] + misses
    out = "\n".join(lines) + "\n"
    (ROOT / results_name).write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
