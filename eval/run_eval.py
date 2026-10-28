"""Evaluate extraction and routing against a labeled dataset in eval/.

    python eval/run_eval.py --file synthetic_dev.jsonl
    python eval/run_eval.py --file synthetic_test.jsonl --model azure:gpt-4.1-mini
    python eval/run_eval.py --file synthetic_dev.jsonl --model gemini-3.5-flash-lite --batch 10
    python eval/run_eval.py --file support_triage.jsonl --profile config/profiles/support.yaml

--profile which profile to run (default PROFILE_PATH). Every key under "expected" in the dataset
          except "team" is scored as an extracted field; "team" is scored as the routing outcome.

--model   models to use, in order (comma separated); overrides LLM_MODELS for this run.
--batch   emails per LLM request. Default is automatic and follows whichever model is
          answering right now: GEMINI_BATCH_SIZE or AZURE_BATCH_SIZE, by the first model in line.
          If Azure fails and Gemini takes over, later requests switch to batches by
          themselves. Pass a number to force one size (1 = no batching).
Extraction answers are cached per (dataset, models, batch size) in eval/.cache/, so a
crash or an exhausted quota resumes where it stopped when you run the same command again.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from app.config import get_settings
from app.enrichment import enrich
from app.extraction.extractor import (
    REFUSED_MODEL,
    LLMUnavailable,
    available_models,
    default_batch_size,
    extract_lead_with_model,
    extract_leads_batch,
)
from app.profile import get_profile, load_profile, pin_profile
from app.routing.engine import route

ROOT = Path(__file__).parent
# The generator appends " Messy 53" to some company names; the model rightly drops it.
MESSY_SUFFIX = re.compile(r"\s+Messy\s+\d+$")
# spam and other are both "not a real lead" and both go to the review queue.
NON_LEAD = {"spam", "other"}
# Sender domains the mock enrichment table knows: enrichment overrides the email's own
# facts, so the generated labels for these rows can disagree with the routing result.
MOCK_DOMAINS = {"acme.com", "bigcorp.com"}


def same(field: str, got, expected) -> bool:
    if field == "company":
        def norm(v):
            return MESSY_SUFFIX.sub("", v).strip().lower() if isinstance(v, str) else v

        return norm(got) == norm(expected)
    if field == "intent" and got in NON_LEAD and expected in NON_LEAD:
        return True
    return got == expected


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
    ap.add_argument("--model", default=None, help="comma-separated models, in order")
    ap.add_argument("--batch", type=int, default=None, help="emails per request (default: auto)")
    ap.add_argument("--profile", default=None, help="profile YAML (default: PROFILE_PATH)")
    args = ap.parse_args()

    if args.model:
        os.environ["LLM_MODELS"] = args.model
        get_settings.cache_clear()
    settings = get_settings()
    if args.profile:
        profile = load_profile(args.profile)
        pin_profile(profile)  # ignore the editor's active-profile choice for this run
    else:
        profile = get_profile()
    Lead = profile.model
    model_list = settings.gemini_model_list
    path = ROOT / args.file
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    rows = rows[: args.limit]

    slug = re.sub(r"[^a-z0-9.]+", "-", "_".join(model_list).lower()).strip("-")
    variant = f"{slug}-b{args.batch or 'auto'}"
    if profile.name != "sales":  # sales keeps its original file names
        variant = f"{profile.name}-{variant}"
    results_name = "results.md" if args.file == "dataset.jsonl" else f"results-{path.stem}.md"
    if args.model or args.batch or profile.name != "sales":
        results_name = results_name.replace(".md", f"-{variant}.md")

    # Extraction answers are saved as they arrive, so a crash or an exhausted quota loses
    # nothing: run the same command again and finished rows are read from the cache.
    cache_path = ROOT / ".cache" / f"{path.stem}__{variant}.jsonl"
    cache_path.parent.mkdir(exist_ok=True)
    cache = load_cache(cache_path)
    models: Counter[str] = Counter()

    # Scored fields: everything the dataset labels except the routing outcome.
    fields = [k for k in rows[0]["expected"] if k != "team"] if rows else []
    todo = [r for r in rows if row_key(r) not in cache]
    print(
        f"{len(rows)} rows, {len(todo)} to extract with {model_list} "
        f"(emails per request: {args.batch or 'auto'})",
        flush=True,
    )
    done = 0
    while done < len(todo):
        # Auto mode re-checks every request, so a failover from Azure to Gemini starts batching.
        size = args.batch or default_batch_size(available_models(model_list) or model_list)
        chunk = todo[done : done + size]
        done += len(chunk)
        print(f"[{done}/{len(todo)}] extracting {len(chunk)} email(s)", flush=True)
        try:
            if size == 1:
                answers = [
                    extract_lead_with_model(r["from"], r["subject"], r["body"]) for r in chunk
                ]
            else:
                answers = extract_leads_batch(chunk)
        except LLMUnavailable as exc:
            hours = exc.retry_after / 3600
            print(
                f"\nPaused: {exc}\nProgress is saved ({len(cache)} rows). "
                f"Re-run the same command in about {hours:.1f}h to resume.",
                flush=True,
            )
            sys.exit(2)
        with cache_path.open("a", encoding="utf-8") as f:
            for r, (lead, model) in zip(chunk, answers, strict=True):
                entry = {"key": row_key(r), "model": model, "lead": lead.model_dump()}
                cache[entry["key"]] = entry
                f.write(json.dumps(entry) + "\n")

    field_hits: dict[str, int] = defaultdict(int)
    confusion: Counter[tuple[str, str]] = Counter()
    team_hits = 0
    mock_rows = mock_hits = 0
    misses: list[str] = []
    field_misses: list[str] = []

    for row in rows:
        entry = cache[row_key(row)]
        lead, model = Lead(**entry["lead"]), entry.get("model")
        models[model or "none (regex fallback)"] += 1
        facts = lead.model_dump()
        if profile.enrich_fill:
            info = enrich(lead.domain)
            for f in profile.enrich_fill:
                if facts.get(f) in (None, ""):
                    facts[f] = info.get(f)
        decision = route(
            facts=facts,
            confidence=lead.confidence,
            refused=model == REFUSED_MODEL,
            profile=profile,
            threshold=settings.confidence_threshold,
            pick_rep=lambda team, reps: reps[0],
        )
        exp = row["expected"]
        for f in fields:
            got = getattr(lead, f, None)  # what the model extracted, before enrichment
            ok = same(f, got, exp[f])
            field_hits[f] += ok
            if not ok:
                field_misses.append(f"- {row['from']}: {f} expected {exp[f]!r}, got {got!r}")
        confusion[(exp["team"], decision.team)] += 1
        domain = row["from"].rsplit("@", 1)[-1].lower()
        mock_row = bool(profile.enrich_fill) and domain in MOCK_DOMAINS
        hit = decision.team == exp["team"]
        team_hits += hit
        if mock_row:
            mock_rows += 1
            mock_hits += hit
        if not hit:
            misses.append(
                f"- {row['from']}: expected {exp['team']}, got {decision.team} "
                f"({decision.rule}; confidence={lead.confidence}; "
                + ", ".join(f"{k}={v}" for k, v in facts.items() if k in fields)
                + ")"
            )

    n = len(rows)
    if n == 0:
        print("no rows evaluated")
        return
    lines = ["# Evaluation results", "", f"Profile: {profile.name} | Samples evaluated: {n}"]
    lines += ["", f"Models: {', '.join(model_list)} | emails per request: {args.batch or 'auto'}"]
    lines += ["", "Answered by: " + ", ".join(f"{m} ({c})" for m, c in models.most_common())]
    if models[REFUSED_MODEL]:
        lines += [
            f"{models[REFUSED_MODEL]} email(s) were refused by every model's content filter and "
            "sent to review (fallback:content_filtered); they count in the numbers below."
        ]
    lines += ["", "## Extraction accuracy", ""]
    lines += [f"- {f}: {field_hits[f] / n:.1%}" for f in fields]
    lines += ["", f"## Routing accuracy: {team_hits / n:.1%} ({team_hits}/{n})", ""]
    if mock_rows:
        clean = (team_hits - mock_hits) / (n - mock_rows)
        lines += [
            f"Excluding {mock_rows} rows from mock-enrichment domains "
            f"(acme.com, bigcorp.com; label conflicts): {clean:.1%} "
            f"({team_hits - mock_hits}/{n - mock_rows})",
            "",
        ]
    lines += [
        "Scoring: company ignores the ' Messy N' suffix and case; intent treats spam and "
        "other as the same bucket.",
        "",
    ]
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
